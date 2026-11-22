-- Creates each service's database and its own login (local compose only).
-- Run by the db-init service on every `docker compose up`, so every
-- statement only creates what is missing and never drops anything.
-- $(CONTACTS_DB_PASSWORD) and $(OVERLAP_DB_PASSWORD) come from .env.

-- contacts-service
IF DB_ID('contacts') IS NULL
    CREATE DATABASE contacts;
GO

IF SUSER_ID('contacts_user') IS NULL
    CREATE LOGIN contacts_user WITH PASSWORD = '$(CONTACTS_DB_PASSWORD)';
GO

USE contacts;
IF USER_ID('contacts_user') IS NULL
    CREATE USER contacts_user FOR LOGIN contacts_user;
-- db_owner inside its own database only, so its migrations can create tables.
ALTER ROLE db_owner ADD MEMBER contacts_user;
GO

-- overlap-service
USE master;
IF DB_ID('overlap') IS NULL
    CREATE DATABASE overlap;
GO

IF SUSER_ID('overlap_user') IS NULL
    CREATE LOGIN overlap_user WITH PASSWORD = '$(OVERLAP_DB_PASSWORD)';
GO

USE overlap;
IF USER_ID('overlap_user') IS NULL
    CREATE USER overlap_user FOR LOGIN overlap_user;
ALTER ROLE db_owner ADD MEMBER overlap_user;
GO
