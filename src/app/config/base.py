from __future__ import annotations

import binascii
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast
import boto3
from dotenv import load_dotenv

from advanced_alchemy.utils.text import slugify
from litestar.data_extractors import RequestExtractorField
from litestar.serialization import decode_json, encode_json
from litestar.utils.module_loader import module_to_os_path
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from ._utils import get_env

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.data_extractors import ResponseExtractorField

DEFAULT_MODULE_NAME = "app"
BASE_DIR: Final[Path] = module_to_os_path(DEFAULT_MODULE_NAME)


@dataclass
class DatabaseSettings:
    ECHO: bool = field(default_factory=get_env("DATABASE_ECHO", False))
    """Enable SQLAlchemy engine logs."""
    ECHO_POOL: bool = field(
        default_factory=get_env("DATABASE_ECHO_POOL", False))
    """Enable SQLAlchemy connection pool logs."""
    POOL_DISABLED: bool = field(
        default_factory=get_env("DATABASE_POOL_DISABLED", False))
    """Disable SQLAlchemy pool configuration."""
    POOL_MAX_OVERFLOW: int = field(
        default_factory=get_env("DATABASE_MAX_POOL_OVERFLOW", 10))
    """Max overflow for SQLAlchemy connection pool"""
    POOL_SIZE: int = field(default_factory=get_env("DATABASE_POOL_SIZE", 5))
    """Pool size for SQLAlchemy connection pool"""
    POOL_TIMEOUT: int = field(
        default_factory=get_env("DATABASE_POOL_TIMEOUT", 30))
    """Time in seconds for timing connections out of the connection pool."""
    POOL_RECYCLE: int = field(
        default_factory=get_env("DATABASE_POOL_RECYCLE", 300))
    """Amount of time to wait before recycling connections."""
    POOL_PRE_PING: bool = field(
        default_factory=get_env("DATABASE_PRE_POOL_PING", False))
    """Optionally ping database before fetching a session from the connection pool."""
    URL: str = field(default_factory=get_env(
        "DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3"))
    """SQLAlchemy Database URL."""
    MIGRATION_CONFIG: str = field(
        default_factory=get_env(
            "DATABASE_MIGRATION_CONFIG", f"{BASE_DIR}/db/migrations/alembic.ini")
    )
    """The path to the `alembic.ini` configuration file."""
    MIGRATION_PATH: str = field(default_factory=get_env(
        "DATABASE_MIGRATION_PATH", f"{BASE_DIR}/db/migrations"))
    """The path to the `alembic` database migrations."""
    MIGRATION_DDL_VERSION_TABLE: str = field(
        default_factory=get_env(
            "DATABASE_MIGRATION_DDL_VERSION_TABLE", "ddl_version")
    )
    """The name to use for the `alembic` versions table name."""
    FIXTURE_PATH: str = field(default_factory=get_env(
        "DATABASE_FIXTURE_PATH", f"{BASE_DIR}/db/fixtures"))
    """The path to JSON fixture files to load into tables."""
    _engine_instance: AsyncEngine | None = None
    """SQLAlchemy engine instance generated from settings."""

    @property
    def engine(self) -> AsyncEngine:
        return self.get_engine()

    def get_engine(self) -> AsyncEngine:
        if self._engine_instance is not None:
            return self._engine_instance
        if self.URL.startswith("postgresql+asyncpg"):
            engine = create_async_engine(
                url=self.URL,
                future=True,
                json_serializer=encode_json,
                json_deserializer=decode_json,
                echo=self.ECHO,
                echo_pool=self.ECHO_POOL,
                max_overflow=self.POOL_MAX_OVERFLOW,
                pool_size=self.POOL_SIZE,
                pool_timeout=self.POOL_TIMEOUT,
                pool_recycle=self.POOL_RECYCLE,
                pool_pre_ping=self.POOL_PRE_PING,
                pool_use_lifo=True,  # use lifo to reduce the number of idle connections
                poolclass=NullPool if self.POOL_DISABLED else None,
            )
            """Database session factory.

            See [`async_sessionmaker()`][sqlalchemy.ext.asyncio.async_sessionmaker].
            """

            @event.listens_for(engine.sync_engine, "connect")
            def _sqla_on_connect(dbapi_connection: Any, _: Any) -> Any:  # pragma: no cover
                """Using msgspec for serialization of the json column values means that the
                output is binary, not `str` like `json.dumps` would output.
                SQLAlchemy expects that the json serializer returns `str` and calls `.encode()` on the value to
                turn it to bytes before writing to the JSONB column. I'd need to either wrap `serialization.to_json` to
                return a `str` so that SQLAlchemy could then convert it to binary, or do the following, which
                changes the behaviour of the dialect to expect a binary value from the serializer.
                See Also https://github.com/sqlalchemy/sqlalchemy/blob/14bfbadfdf9260a1c40f63b31641b27fe9de12a0/lib/sqlalchemy/dialects/postgresql/asyncpg.py#L934  pylint: disable=line-too-long
                """

                def encoder(bin_value: bytes) -> bytes:
                    return b"\x01" + encode_json(bin_value)

                def decoder(bin_value: bytes) -> Any:
                    # the byte is the \x01 prefix for jsonb used by PostgreSQL.
                    # asyncpg returns it when format='binary'
                    return decode_json(bin_value[1:])

                dbapi_connection.await_(
                    dbapi_connection.driver_connection.set_type_codec(
                        "jsonb",
                        encoder=encoder,
                        decoder=decoder,
                        schema="pg_catalog",
                        format="binary",
                    ),
                )
                dbapi_connection.await_(
                    dbapi_connection.driver_connection.set_type_codec(
                        "json",
                        encoder=encoder,
                        decoder=decoder,
                        schema="pg_catalog",
                        format="binary",
                    ),
                )
        elif self.URL.startswith("sqlite+aiosqlite"):
            engine = create_async_engine(
                url=self.URL,
                future=True,
                json_serializer=encode_json,
                json_deserializer=decode_json,
                echo=self.ECHO,
                echo_pool=self.ECHO_POOL,
                pool_recycle=self.POOL_RECYCLE,
                pool_pre_ping=self.POOL_PRE_PING,
            )
            """Database session factory.

            See [`async_sessionmaker()`][sqlalchemy.ext.asyncio.async_sessionmaker].
            """

            @event.listens_for(engine.sync_engine, "connect")
            def _sqla_on_connect(dbapi_connection: Any, _: Any) -> Any:  # pragma: no cover
                """Override the default begin statement.  The disables the built in begin execution."""
                dbapi_connection.isolation_level = None

            @event.listens_for(engine.sync_engine, "begin")
            def _sqla_on_begin(dbapi_connection: Any) -> Any:  # pragma: no cover
                """Emits a custom begin"""
                dbapi_connection.exec_driver_sql("BEGIN")
        else:
            engine = create_async_engine(
                url=self.URL,
                future=True,
                json_serializer=encode_json,
                json_deserializer=decode_json,
                echo=self.ECHO,
                echo_pool=self.ECHO_POOL,
                max_overflow=self.POOL_MAX_OVERFLOW,
                pool_size=self.POOL_SIZE,
                pool_timeout=self.POOL_TIMEOUT,
                pool_recycle=self.POOL_RECYCLE,
                pool_pre_ping=self.POOL_PRE_PING,
                pool_use_lifo=True,  # use lifo to reduce the number of idle connections
                poolclass=NullPool if self.POOL_DISABLED else None,
            )
        self._engine_instance = engine
        return self._engine_instance


@dataclass
class ServerSettings:
    """Server configurations."""

    HOST: str = field(default_factory=get_env("LITESTAR_HOST", "0.0.0.0"))  # noqa: S104
    """Server network host."""
    PORT: int = field(default_factory=get_env("LITESTAR_PORT", 8000))
    """Server port."""
    KEEPALIVE: int = field(default_factory=get_env("LITESTAR_KEEPALIVE", 65))
    """Seconds to hold connections open (65 is > AWS lb idle timeout)."""
    RELOAD: bool = field(default_factory=get_env("LITESTAR_RELOAD", False))
    """Turn on hot reloading."""
    RELOAD_DIRS: list[str] = field(default_factory=get_env(
        "LITESTAR_RELOAD_DIRS", [f"{BASE_DIR}"]))
    """Directories to watch for reloading."""


@dataclass
class LogSettings:
    """Logger configuration"""

    # https://stackoverflow.com/a/1845097/6560549
    EXCLUDE_PATHS: str = r"\A(?!x)x"
    """Regex to exclude paths from logging."""
    HTTP_EVENT: str = "HTTP"
    """Log event name for logs from Litestar handlers."""
    INCLUDE_COMPRESSED_BODY: bool = False
    """Include 'body' of compressed responses in log output."""
    LEVEL: int = field(default_factory=get_env("LOG_LEVEL", 30))
    """Stdlib log levels.

    Only emit logs at this level, or higher.
    """
    OBFUSCATE_COOKIES: set[str] = field(
        default_factory=lambda: {"session", "XSRF-TOKEN"})
    """Request cookie keys to obfuscate."""
    OBFUSCATE_HEADERS: set[str] = field(
        default_factory=lambda: {"Authorization", "X-API-KEY", "X-XSRF-TOKEN"})
    """Request header keys to obfuscate."""
    JOB_FIELDS: list[str] = field(
        default_factory=lambda: [
            "function",
            "kwargs",
            "key",
            "scheduled",
            "attempts",
            "completed",
            "queued",
            "started",
            "result",
            "error",
        ],
    )
    """Job attributes to be logged."""
    REQUEST_FIELDS: list[RequestExtractorField] = field(
        default_factory=get_env(
            "LOG_REQUEST_FIELDS",
            [
                "path",
                "method",
                "query",
                "path_params",
            ],
            list[RequestExtractorField],
        ),
    )
    """Attributes of the [Request][litestar.connection.request.Request] to be
    logged."""
    RESPONSE_FIELDS: list[ResponseExtractorField] = field(
        default_factory=cast(
            "Callable[[],list[ResponseExtractorField]]",
            get_env(
                "LOG_RESPONSE_FIELDS",
                ["status_code"],
            ),
        )
    )
    """Attributes of the [Response][litestar.response.Response] to be
    logged."""
    SQLALCHEMY_LEVEL: int = field(
        default_factory=get_env("SQLALCHEMY_LOG_LEVEL", 30))
    """Level to log SQLAlchemy logs."""
    ASGI_ACCESS_LEVEL: int = field(
        default_factory=get_env("ASGI_ACCESS_LOG_LEVEL", 30))
    """Level to log uvicorn access logs."""
    ASGI_ERROR_LEVEL: int = field(
        default_factory=get_env("ASGI_ERROR_LOG_LEVEL", 30))
    """Level to log uvicorn error logs."""


@dataclass
class AppSettings:
    """Application configuration"""

    APP_LOC: str = "app.asgi:create_app"
    """Path to app executable, or factory."""
    URL: str = field(default_factory=get_env(
        "APP_URL", "http://localhost:8000"))
    """The frontend base URL"""
    DEBUG: bool = field(default_factory=get_env("LITESTAR_DEBUG", False))
    """Run `Litestar` with `debug=True`."""
    SECRET_KEY: str = field(
        default_factory=get_env("SECRET_KEY", binascii.hexlify(
            os.urandom(32)).decode(encoding="utf-8")),
    )
    """Application secret key."""
    NAME: str = field(default_factory=lambda: "app")
    """Application name."""
    ALLOWED_CORS_ORIGINS: list[str] | str = field(
        default_factory=get_env("ALLOWED_CORS_ORIGINS", ["*"], list[str]))
    """Allowed CORS Origins"""
    CSRF_COOKIE_NAME: str = field(
        default_factory=get_env("CSRF_COOKIE_NAME", "XSRF-TOKEN"))
    """CSRF Cookie Name"""
    CSRF_COOKIE_SECURE: bool = field(
        default_factory=get_env("CSRF_COOKIE_SECURE", False))
    """CSRF Secure Cookie"""
    JWT_ENCRYPTION_ALGORITHM: str = field(default_factory=lambda: "HS256")
    """JWT Encryption Algorithm"""
    GITHUB_OAUTH2_CLIENT_ID: str = field(
        default_factory=get_env("GITHUB_OAUTH2_CLIENT_ID", ""))
    """Github OAuth2 Client ID"""
    GITHUB_OAUTH2_CLIENT_SECRET: str = field(
        default_factory=get_env("GITHUB_OAUTH2_CLIENT_SECRET", ""))
    """Github OAuth2 Client Secret"""

    @property
    def slug(self) -> str:
        """Return a slugified name.

        Returns:
            `self.NAME`, all lowercase and hyphens instead of spaces.
        """
        return slugify(self.NAME)

    def __post_init__(self) -> None:
        # Check if the ALLOWED_CORS_ORIGINS is a string.
        if isinstance(self.ALLOWED_CORS_ORIGINS, str):
            # Check if the string starts with "[" and ends with "]", indicating a list.
            if self.ALLOWED_CORS_ORIGINS.startswith("[") and self.ALLOWED_CORS_ORIGINS.endswith("]"):
                try:
                    # Safely evaluate the string as a Python list.
                    self.ALLOWED_CORS_ORIGINS = json.loads(
                        self.ALLOWED_CORS_ORIGINS)
                except (SyntaxError, ValueError):
                    # Handle potential errors if the string is not a valid Python literal.
                    msg = "ALLOWED_CORS_ORIGINS is not a valid list representation."
                    raise ValueError(msg) from None
            else:
                # Split the string by commas into a list if it is not meant to be a list representation.
                self.ALLOWED_CORS_ORIGINS = [
                    host.strip() for host in self.ALLOWED_CORS_ORIGINS.split(",")]


@dataclass
class S3Settings:
    """S3 Client configurations."""

    ACCESS_KEY: str | None = field(default_factory=get_env("S3_ACCESS_KEY", None))
    """S3 Access Key"""
    SECRET_KEY: str | None = field(default_factory=get_env("S3_SECRET_KEY", None))
    """S3 Secret Key"""
    BUCKET_NAME: str | None = field(default_factory=get_env("S3_BUCKET_NAME", None))
    """S3 Bucket Name"""
    ENDPOINT_URL: str | None = field(default_factory=get_env("S3_ENDPOINT_URL", None))
    """S3 Endpoint URL"""
    REGION: str | None = field(default_factory=get_env("S3_REGION", None))
    """S3 Region"""
    _client: Any | None = None

    @property
    def client(self) -> Any:
        """Get Boto3 S3 client."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.ENDPOINT_URL,
                aws_access_key_id=self.ACCESS_KEY,
                aws_secret_access_key=self.SECRET_KEY,
                region_name=self.REGION,
            )
        return self._client


@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    log: LogSettings = field(default_factory=LogSettings)
    s3: S3Settings = field(default_factory=S3Settings)

    @classmethod
    def from_env(cls, dotenv_filename: str = ".env") -> Settings:
        from litestar.cli._utils import console

        env_file = Path(f"{os.curdir}/{dotenv_filename}")
        if env_file.is_file():
            from dotenv import load_dotenv

            console.print(
                f"[yellow]Loading environment configuration from {dotenv_filename}[/]")

            load_dotenv(env_file, override=True)
        return Settings()


@lru_cache(maxsize=1, typed=True)
def get_settings() -> Settings:
    return Settings.from_env()
