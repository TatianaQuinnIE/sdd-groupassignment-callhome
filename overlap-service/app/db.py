# SQL Local and Azure SQL Database
import pymssql

from app.config import Settings


def connect(settings: Settings):
    return pymssql.connect(
        server=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        login_timeout=10,
        timeout=30,
    )
