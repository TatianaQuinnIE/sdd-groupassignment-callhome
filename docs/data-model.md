# Data model

Each service has its own database on the shared SQL Server and its own login. Services do not read each other's tables. overlap-service gets contact details from contacts-service over HTTP.

## overlap-service

The tables below were added by migrations `001_create_holiday_cache.sql` and `002_create_my_schedule.sql`.

### `holiday_cache_status`

Tracks which country and year have been checked, including years with no holidays.

| Column | Type | Notes |
| --- | --- | --- |
| `country_code` | `CHAR(2)` | Part of the primary key |
| `year` | `SMALLINT` | Part of the primary key |
| `fetched_at` | `DATETIME2` | Defaults to the current UTC time |

### `holiday_cache`

Stores public holidays returned by Nager.Date.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `INT IDENTITY` | Primary key |
| `country_code`, `year` | `CHAR(2)`, `SMALLINT` | Foreign key to `holiday_cache_status` |
| `holiday_date` | `DATE` | Holiday date in that country |
| `local_name` | `NVARCHAR(200)` | Name in the local language |
| `name` | `NVARCHAR(200)` | English name |
| `is_global` | `BIT` | Defaults to 1; regional holidays are not shown |

There is a unique constraint on (`country_code`, `holiday_date`, `name`) and an index on (`country_code`, `holiday_date`) for lookups.

### `my_settings` and `my_busy_blocks`

I built these tables for the “My week” feature. `my_settings` stores my time zone and sleep times. `my_busy_blocks` stores weekly busy times, where weekday 0 is Monday, along with the start time, end time, and label.

## contacts-service

Alexandra built the contacts and call-log tables. The call log is used to get each contact's `last_called` value.

## How the two services connect

overlap-service gets `time_zone`, `country_code`, `call_minutes`, `call_every_days`, and `last_called` from contacts-service through `GET /contacts`. It uses `country_code` to look up public holidays.
