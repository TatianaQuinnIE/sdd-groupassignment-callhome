# SQL Local and Azure SQL Database
import pymssql

from app.config import Settings


def connect(settings: Settings, login_timeout: int = 10, timeout: int = 30):
    return pymssql.connect(
        server=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        login_timeout=login_timeout,
        timeout=timeout,
    )
