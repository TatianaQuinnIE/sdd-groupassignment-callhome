-- 002: the calls you made to each contact. Feeds "last called" and the overdue ranking.
CREATE TABLE call_logs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    contact_id INT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    called_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),  -- stored in UTC
    minutes INT NULL,
    note NVARCHAR(500) NULL
);
CREATE INDEX ix_call_logs_contact_called ON call_logs (contact_id, called_at DESC);
