# Monitoring

Everything is built on the Log Analytics workspace `sdd-3b-g5-logs`, which the Container
Apps environment sends all container output to. Defined in
[`infra/monitoring.bicep`](../infra/monitoring.bicep).

## Where the data comes from

Each service logs one line per request at INFO level, with no request bodies
(`app/logging_middleware.py`):

```
2026-11-22 17:50:30,888 INFO contacts.requests method=GET path=/contacts status=200 duration_ms=44.3
```

These lines land in the table `ContainerAppConsoleLogs_CL`, column `Log_s`. The workspace
keeps them 30 days and caps ingestion at 1 GB a day.

## The dashboard

**Azure portal > Monitor > Workbooks > `sdd-3b-g5 monitoring`** (or open the workspace
`sdd-3b-g5-logs` > Workbooks). One page with:

| Chart | What it shows |
| --- | --- |
| Request count per hour | Traffic per service |
| Error rate (5xx %) per hour | Share of requests the service failed |
| Response time p50 / p95 (ms) | Typical and slow-end latency per service |
| SLO table | The SLO below, always over the last 7 days |

The time range at the top (1 hour to 7 days) applies to the three charts. `/health` calls
are left out: the pipeline makes them on every deploy, so they say nothing about real use.

The same queries are saved in the workspace under **Logs > Queries > Calling-home planner**,
so they can be run and changed by hand.

## Queries

`RequestLogs` is a saved workspace function that turns the log line into columns. The other
queries start from it.

```kusto
// RequestLogs
ContainerAppConsoleLogs_CL
| where Log_s has ".requests method="
| parse Log_s with * " method=" Method " path=" Path " status=" Status:int " duration_ms=" DurationMs:real
| extend Service = replace_string(ContainerAppName_s, "sdd-3b-g5-", "")
| project TimeGenerated, Service, Method, Path, Status, DurationMs
```

```kusto
// Request count per service
RequestLogs
| where Path != "/health"
| summarize Requests = count() by Service, bin(TimeGenerated, 1h)
| render timechart
```

```kusto
// Error rate (5xx %) per service
RequestLogs
| where Path != "/health"
| summarize Requests = count(), Errors = countif(Status >= 500) by Service, bin(TimeGenerated, 1h)
| extend ErrorRatePct = round(100.0 * Errors / Requests, 2)
| project TimeGenerated, Service, ErrorRatePct
| render timechart
```

```kusto
// Response time p50 / p95 per service
RequestLogs
| where Path != "/health"
| summarize p50_ms = percentile(DurationMs, 50), p95_ms = percentile(DurationMs, 95) by Service, bin(TimeGenerated, 1h)
| render timechart
```

## SLO

**99% of `GET /contacts` requests are answered without a server error in under 500 ms,
measured over the last 7 days.**

`GET /contacts` is the request every page of the UI starts with, so if it is slow or
failing, the whole app feels broken. 500 ms is well above what we see normally (p95 around
75 ms on 22 Nov) and leaves room for a database that has just resumed. The error budget is
the 1% of requests allowed to miss.

```kusto
RequestLogs
| where TimeGenerated > ago(7d)
| where Service == "contacts" and Method == "GET" and Path == "/contacts"
| summarize Total = count(), Good = countif(Status < 500 and DurationMs < 500)
| extend SloTargetPct = 99.0, AchievedPct = round(100.0 * Good / Total, 2)
| extend ErrorBudgetLeftPct = round(100.0 * (1 - (Total - Good) / (0.01 * Total)), 1)
| extend Met = AchievedPct >= SloTargetPct
```

Status on 22 Nov: 16 of 16 requests good, 100% achieved, error budget untouched.

### What the SLO does not see

- **Cold starts.** After a quiet period the first request gets 503 "App port is not
  ready" from Azure while the container starts. That answer comes from Azure's ingress,
  not our code, so it never appears in our log lines. The UI tells the user the service
  may be starting up and offers a retry (see decision record 3).
- **Low traffic.** With a handful of requests a day, one slow request is more than 1% of
  the total. The number is only meaningful once there is real use.

## Deploying it

After `infra/main.bicep` (the workspace must exist):

```bash
az provider register -n Microsoft.Insights
az deployment group create -g rg-sdd-3b-g5 -f infra/monitoring.bicep
```
