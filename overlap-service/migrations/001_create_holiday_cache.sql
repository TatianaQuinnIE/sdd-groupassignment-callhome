-- 001: public-holiday cache filled from Nager.Date, one fetch per country and year.
-- holiday_cache_status records that a country+year was fetched, even when it has no holidays.
CREATE TABLE holiday_cache_status (
    country_code CHAR(2) NOT NULL,
    year SMALLINT NOT NULL,
    fetched_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_holiday_cache_status PRIMARY KEY (country_code, year)
);

CREATE TABLE holiday_cache (
    id INT IDENTITY(1,1) PRIMARY KEY,
    country_code CHAR(2) NOT NULL,
    year SMALLINT NOT NULL,
    holiday_date DATE NOT NULL,
    local_name NVARCHAR(200) NOT NULL,
    name NVARCHAR(200) NOT NULL,
    is_global BIT NOT NULL DEFAULT 1,
    CONSTRAINT uq_holiday_cache UNIQUE (country_code, holiday_date, name),
    CONSTRAINT fk_holiday_cache_status FOREIGN KEY (country_code, year)
        REFERENCES holiday_cache_status (country_code, year)
);

CREATE INDEX ix_holiday_cache_lookup ON holiday_cache (country_code, holiday_date);
