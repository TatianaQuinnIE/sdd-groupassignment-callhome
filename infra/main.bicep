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

output logAnalyticsWorkspace string = logs.name
output containerAppsEnvironment string = env.name
