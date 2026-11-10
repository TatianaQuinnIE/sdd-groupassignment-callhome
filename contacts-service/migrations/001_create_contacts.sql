-- 001: contacts, the core entity of the Calling-home planner.
CREATE TABLE contacts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    city NVARCHAR(100) NOT NULL,
    time_zone NVARCHAR(64) NOT NULL,          -- IANA name, e.g. 'Asia/Seoul'
    country_code CHAR(2) NOT NULL,            -- ISO 3166, used for holidays
    sleep_start TIME NOT NULL DEFAULT '23:00',
    sleep_end TIME NOT NULL DEFAULT '07:00',
    call_minutes INT NOT NULL DEFAULT 30,
    call_every_days INT NOT NULL DEFAULT 7,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
