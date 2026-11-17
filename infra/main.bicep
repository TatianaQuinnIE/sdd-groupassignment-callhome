// Azure resources for the Calling-home planner (group sdd-3b-g5).
//
// Deployed into the existing resource group rg-sdd-3b-g5 (we are not allowed to
// create resource groups). Run once by hand for the initial setup; after that
// only the pipeline changes anything. Commands are in the README.

targetScope = 'resourceGroup'

@description('Prefix for every resource name: sdd-<class>-g<N>.')
param prefix string = 'sdd-3b-g5'

@description('Region for everything. The group resource group is in westeurope.')
param location string = resourceGroup().location

@description('SQL server admin login. Used only for the one-off setup (creating the per-service users).')
param sqlAdminLogin string = 'sqladmin-${prefix}'

@description('SQL server admin password. Passed in at deploy time, never stored in the repository.')
@secure()
param sqlAdminPassword string

@description('Password of the contacts_app database user. Also stored as a GitHub secret for the pipeline.')
@secure()
param contactsDbPassword string

@description('Password of the overlap_app database user. Also stored as a GitHub secret for the pipeline.')
@secure()
param overlapDbPassword string

@description('Image for both apps at first setup. The pipeline replaces it with ghcr.io/<owner>/<service>:<commit SHA>.')
param placeholderImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Port the container listens on. The placeholder listens on 80; our FastAPI images listen on 8000, and the first pipeline deploy switches it.')
param targetPort int = 80

// Monitoring: Log Analytics workspace
// The Container Apps environment sends every container's stdout here, so the
// request log lines (method, path, status, duration) can be queried with KQL.
// The daily cap keeps log volume and cost low, as the brief asks.

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

// Container Apps environment (Consumption plan)
// Both services run in this one environment. Consumption means we pay only
// while a container is running, and the apps can scale to zero.

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

// SQL server and one serverless database per service
// One logical server, two databases: each service owns its own data and only
// gets a user for its own database. Serverless General Purpose, 0.5-1 vCore,
// auto-pause after 15 minutes and 2 GB max, as the professor's guide sets for
// the group subscription (no free offer there).

resource sql 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: '${prefix}-sql'
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

// 0.0.0.0 to 0.0.0.0 is Azure's special rule for "allow Azure services",
// so the Container Apps can reach the server. No other IPs are open.
resource allowAzure 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = {
  parent: sql
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

var databases = [
  'contacts'
  'overlap'
]

resource dbs 'Microsoft.Sql/servers/databases@2023-08-01-preview' = [
  for service in databases: {
    parent: sql
    name: '${prefix}-${service}-db'
    location: location
    sku: {
      name: 'GP_S_Gen5'
      tier: 'GeneralPurpose'
      family: 'Gen5'
      capacity: 1
    }
    properties: {
      minCapacity: json('0.5')
      autoPauseDelay: 15
      maxSizeBytes: 2147483648
      requestedBackupStorageRedundancy: 'Local'
      zoneRedundant: false
    }
  }
]

// Static Web App for the UI
// Free tier, one per group, named <prefix>-ui as the brief requires. Its
// address is the only origin the services accept (CORS).

resource ui 'Microsoft.Web/staticSites@2023-12-01' = {
  name: '${prefix}-ui'
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {}
}

var uiOrigin = 'https://${ui.properties.defaultHostname}'
var sqlHost = sql.properties.fullyQualifiedDomainName

// Container Apps: one per service
// Scale to zero, at most 1 replica, smallest size. Configuration comes only
// from environment variables; the database password is a Container Apps
// secret, referenced with secretRef so it never shows in plain text.
// CORS is handled in the FastAPI code (CORS_ORIGINS), not by the ingress:
// the ingress CORS setting breaks POST/PUT preflights from the browser.

resource contacts 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-contacts'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
      }
      secrets: [
        {
          name: 'db-password'
          value: contactsDbPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'contacts-service'
          image: placeholderImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'DB_HOST', value: sqlHost }
            { name: 'DB_PORT', value: '1433' }
            { name: 'DB_NAME', value: '${prefix}-contacts-db' }
            { name: 'DB_USER', value: 'contacts_app' }
            { name: 'DB_PASSWORD', secretRef: 'db-password' }
            { name: 'CORS_ORIGINS', value: uiOrigin }
            { name: 'RUN_MIGRATIONS', value: 'true' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource overlap 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-overlap'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
      }
      secrets: [
        {
          name: 'db-password'
          value: overlapDbPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'overlap-service'
          image: placeholderImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'DB_HOST', value: sqlHost }
            { name: 'DB_PORT', value: '1433' }
            { name: 'DB_NAME', value: '${prefix}-overlap-db' }
            { name: 'DB_USER', value: 'overlap_app' }
            { name: 'DB_PASSWORD', secretRef: 'db-password' }
            { name: 'CORS_ORIGINS', value: uiOrigin }
            { name: 'RUN_MIGRATIONS', value: 'true' }
            { name: 'CONTACTS_SERVICE_URL', value: 'https://${contacts.properties.configuration.ingress.fqdn}' }
            { name: 'CONTACTS_TIMEOUT_S', value: '3' }
            { name: 'NAGER_BASE_URL', value: 'https://date.nager.at/api/v3' }
            { name: 'NAGER_TIMEOUT_S', value: '3' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output logAnalyticsWorkspace string = logs.name
output containerAppsEnvironment string = env.name
output sqlServerHost string = sql.properties.fullyQualifiedDomainName
output uiUrl string = uiOrigin
output contactsUrl string = 'https://${contacts.properties.configuration.ingress.fqdn}'
output overlapUrl string = 'https://${overlap.properties.configuration.ingress.fqdn}'
