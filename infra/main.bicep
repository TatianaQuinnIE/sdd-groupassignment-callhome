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

// ---------------------------------------------------------------------------
// Monitoring: Log Analytics workspace
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Container Apps environment (Consumption plan)
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// SQL server and one serverless database per service
// ---------------------------------------------------------------------------
// One logical server, two databases: each service owns its own data and only
// gets a user for its own database. Serverless General Purpose, 0.5–1 vCore,
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

output logAnalyticsWorkspace string = logs.name
output containerAppsEnvironment string = env.name
output sqlServerHost string = sql.properties.fullyQualifiedDomainName
