// Monitoring: saved Log Analytics queries, a Workbook dashboard and the SLO.
//
// Both services write one line per request to stdout, for example
//   ... INFO contacts.requests method=GET path=/contacts status=200 duration_ms=44.3
// and the Container Apps environment sends stdout to the workspace in main.bicep
// (table ContainerAppConsoleLogs_CL). Everything here is built on that line.
// Deployed by hand after main.bicep; commands and the queries are in docs/monitoring.md.

targetScope = 'resourceGroup'

param prefix string = 'sdd-3b-g5'
param location string = resourceGroup().location

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: '${prefix}-logs'
}

// RequestLogs: a workspace function that turns the raw log line into columns
// (Service, Method, Path, Status, DurationMs). The other queries start from it.
var requestLogsQuery = replace(
  '''
ContainerAppConsoleLogs_CL
| where Log_s has ".requests method="
| parse Log_s with * " method=" Method " path=" Path " status=" Status:int " duration_ms=" DurationMs:real
| extend Service = replace_string(ContainerAppName_s, "PREFIX-", "")
| project TimeGenerated, Service, Method, Path, Status, DurationMs
''',
  'PREFIX',
  prefix
)

// The pipeline calls /health on every deploy; leaving it out keeps the numbers
// about real use of the app.
var requestCountQuery = '''
RequestLogs
| where Path != "/health"
| summarize Requests = count() by Service, bin(TimeGenerated, 1h)
| render timechart
'''

var errorRateQuery = '''
RequestLogs
| where Path != "/health"
| summarize Requests = count(), Errors = countif(Status >= 500) by Service, bin(TimeGenerated, 1h)
| extend ErrorRatePct = round(100.0 * Errors / Requests, 2)
| project TimeGenerated, Service, ErrorRatePct
| render timechart
'''

var responseTimeQuery = '''
RequestLogs
| where Path != "/health"
| summarize p50_ms = percentile(DurationMs, 50), p95_ms = percentile(DurationMs, 95) by Service, bin(TimeGenerated, 1h)
| render timechart
'''

// SLO: 99% of GET /contacts answered in under 500 ms, over the last 7 days.
// Error budget = the 1% of requests allowed to be slow or fail.
var sloQuery = '''
RequestLogs
| where TimeGenerated > ago(7d)
| where Service == "contacts" and Method == "GET" and Path == "/contacts"
| summarize Total = count(), Good = countif(Status < 500 and DurationMs < 500)
| extend SloTargetPct = 99.0, AchievedPct = round(100.0 * Good / Total, 2)
| extend ErrorBudgetLeftPct = round(100.0 * (1 - (Total - Good) / (0.01 * Total)), 1)
| extend Met = AchievedPct >= SloTargetPct
'''

var savedQueries = [
  {
    name: 'request-logs'
    displayName: 'RequestLogs (parsed request lines)'
    query: requestLogsQuery
    functionAlias: 'RequestLogs'
  }
  {
    name: 'request-count'
    displayName: 'Request count per service'
    query: requestCountQuery
    functionAlias: ''
  }
  {
    name: 'error-rate'
    displayName: 'Error rate (5xx %) per service'
    query: errorRateQuery
    functionAlias: ''
  }
  {
    name: 'response-time'
    displayName: 'Response time p50 / p95 per service'
    query: responseTimeQuery
    functionAlias: ''
  }
  {
    name: 'slo-get-contacts'
    displayName: 'SLO: 99% of GET /contacts under 500 ms (7 days)'
    query: sloQuery
    functionAlias: ''
  }
]

// The function has to exist before the queries that use it.
@batchSize(1)
resource saved 'Microsoft.OperationalInsights/workspaces/savedSearches@2020-08-01' = [
  for q in savedQueries: {
    parent: logs
    name: q.name
    properties: union(
      {
        category: 'Calling-home planner'
        displayName: q.displayName
        query: q.query
        version: 2
      },
      empty(q.functionAlias) ? {} : { functionAlias: q.functionAlias }
    )
  }
]

// Workbook: one page with the three charts and the SLO table. The charts
// follow the time range picked at the top; the SLO is always the last 7 days.
func chart(name string, title string, query string, viz string) object => {
  type: 3
  name: name
  content: {
    version: 'KqlItem/1.0'
    title: title
    query: query
    size: 0
    timeContextFromParameter: 'TimeRange'
    queryType: 0
    resourceType: 'microsoft.operationalinsights/workspaces'
    visualization: viz
  }
}

var workbook = {
  version: 'Notebook/1.0'
  items: [
    {
      type: 1
      name: 'intro'
      content: {
        json: '## Calling-home planner\nRequests to contacts-service and overlap-service, from their request log lines. `/health` calls from the pipeline are left out.'
      }
    }
    {
      type: 9
      name: 'parameters'
      content: {
        version: 'KqlParameterItem/1.0'
        parameters: [
          {
            id: 'a1f3c2d4-0000-4000-8000-000000000001'
            version: 'KqlParameterItem/1.0'
            name: 'TimeRange'
            label: 'Time range'
            type: 4
            isRequired: true
            value: {
              durationMs: 86400000
            }
            typeSettings: {
              selectableValues: [
                { durationMs: 3600000 }
                { durationMs: 86400000 }
                { durationMs: 259200000 }
                { durationMs: 604800000 }
              ]
            }
          }
        ]
      }
    }
    chart('request-count', 'Request count per hour', requestCountQuery, 'timechart')
    chart('error-rate', 'Error rate (5xx %) per hour', errorRateQuery, 'timechart')
    chart('response-time', 'Response time p50 / p95 (ms)', responseTimeQuery, 'timechart')
    {
      type: 3
      name: 'slo'
      content: {
        version: 'KqlItem/1.0'
        title: 'SLO: 99% of GET /contacts under 500 ms, last 7 days'
        query: sloQuery
        size: 4
        timeContext: {
          durationMs: 604800000
        }
        queryType: 0
        resourceType: 'microsoft.operationalinsights/workspaces'
        visualization: 'table'
      }
    }
  ]
  fallbackResourceIds: [
    logs.id
  ]
}

resource dashboard 'Microsoft.Insights/workbooks@2023-06-01' = {
  name: guid(resourceGroup().id, '${prefix}-monitoring')
  location: location
  kind: 'shared'
  properties: {
    displayName: '${prefix} monitoring'
    category: 'workbook'
    sourceId: logs.id
    serializedData: string(workbook)
  }
  dependsOn: [
    saved
  ]
}

output workbookId string = dashboard.id
