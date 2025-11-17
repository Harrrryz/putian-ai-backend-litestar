# Database Setup & Migrations

This document provides comprehensive guidance for database setup, migration management, and operational procedures for the Litestar Todo application.

## Table of Contents

1. [Database Architecture Overview](#database-architecture-overview)
2. [Supported Database Systems](#supported-database-systems)
3. [Database Configuration](#database-configuration)
4. [Connection Setup](#connection-setup)
5. [Migration Management](#migration-management)
6. [Connection Pooling](#connection-pooling)
7. [Database Testing](#database-testing)
8. [Multi-Environment Configuration](#multi-environment-configuration)
9. [Performance & Optimization](#performance--optimization)
10. [Backup & Recovery](#backup--recovery)
11. [Troubleshooting](#troubleshooting)

## Database Architecture Overview

The application uses a sophisticated database architecture built on:

- **Advanced Alchemy**: Enhanced SQLAlchemy with repository pattern
- **Alembic**: Database migration management system
- **Async Operations**: Full async/await support with AsyncSession
- **Multi-Database Support**: PostgreSQL (production) and SQLite (development/testing)

### Core Components

- **Models**: Located in `src/app/db/models/`
- **Migrations**: Located in `src/app/db/migrations/versions/`
- **Configuration**: Managed in `src/app/config/base.py`
- **Database Engine**: Async SQLAlchemy engine with connection pooling

## Supported Database Systems

### PostgreSQL (Primary)
- **Driver**: `asyncpg` (async PostgreSQL driver)
- **Recommended for**: Production environments
- **Features**: Full feature support, connection pooling, advanced types

### SQLite (Development/Testing)
- **Driver**: `aiosqlite` (async SQLite driver)
- **Recommended for**: Development, testing, lightweight deployments
- **Features**: Simple setup, file-based storage, limited feature set

### Supported URL Formats

```bash
# PostgreSQL
postgresql+asyncpg://user:password@host:port/database

# SQLite
sqlite+aiosqlite:///path/to/database.sqlite3
sqlite+aiosqlite:///:memory:
```

## Database Configuration

### Environment Variables

All database configuration is managed through environment variables:

#### Core Database Settings
```bash
# Database connection URL (required)
DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15432/app

# SQLAlchemy query logging
DATABASE_ECHO=false
DATABASE_ECHO_POOL=false

# Connection pool settings
DATABASE_POOL_DISABLED=false
DATABASE_POOL_SIZE=5
DATABASE_MAX_POOL_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=300
DATABASE_PRE_POOL_PING=false
```

#### Migration Settings
```bash
# Alembic migration configuration
DATABASE_MIGRATION_CONFIG=src/app/db/migrations/alembic.ini
DATABASE_MIGRATION_PATH=src/app/db/migrations
DATABASE_MIGRATION_DDL_VERSION_TABLE=ddl_version

# Database fixtures path
DATABASE_FIXTURE_PATH=src/app/db/fixtures
```

### Configuration Classes

The database configuration is defined in `src/app/config/base.py`:

```python
@dataclass
class DatabaseSettings:
    URL: str = field(default_factory=get_env(
        "DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3"))
    ECHO: bool = field(default_factory=get_env("DATABASE_ECHO", False))
    POOL_SIZE: int = field(default_factory=get_env("DATABASE_POOL_SIZE", 5))
    # ... additional pool configuration
```

## Connection Setup

### PostgreSQL Connection

For PostgreSQL, the application uses asyncpg with custom JSON handling:

```python
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
    pool_use_lifo=True,
    poolclass=NullPool if self.POOL_DISABLED else None,
)
```

#### JSON/JSONB Support
The PostgreSQL connection includes custom codecs for efficient JSON handling:

```python
@event.listens_for(engine.sync_engine, "connect")
def _sqla_on_connect(dbapi_connection: Any, _: Any) -> Any:
    def encoder(bin_value: bytes) -> bytes:
        return b"\x01" + encode_json(bin_value)

    def decoder(bin_value: bytes) -> Any:
        return decode_json(bin_value[1:])

    # Configure JSONB and JSON codecs
    dbapi_connection.await_(
        dbapi_connection.driver_connection.set_type_codec(
            "jsonb", encoder=encoder, decoder=decoder,
            schema="pg_catalog", format="binary"
        )
    )
```

### SQLite Connection

SQLite configuration is simpler with basic async support:

```python
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
```

## Migration Management

### Alembic Configuration

The migration system uses Alembic with Advanced Alchemy integration:

#### Configuration File
Located at `src/app/db/migrations/alembic.ini`:

```ini
[alembic]
prepend_sys_path = src:.
script_location = src/app/lib/db/migrations
file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s_%%(rev)s
timezone = UTC
truncate_slug_length = 40
version_path_separator = os
output_encoding = utf-8
```

#### Migration Environment
The environment file (`src/app/db/migrations/env.py`) provides:

- Online/offline migration modes
- Column ordering for consistency
- Async migration support
- Custom directive processing

### Migration Commands

Using the Litestar CLI:

```bash
# Create new migration
uv run app database revision --autogenerate -m "Add new feature"

# Apply migrations
uv run app database upgrade

# Rollback migrations
uv run app database downgrade

# Show current revision
uv run app database current

# Show migration history
uv run app database history
```

#### Alternative Direct Commands

```bash
# Using Alembic directly
uv run alembic revision --autogenerate -m "Add new table"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic current
uv run alembic history
```

### Migration File Structure

Each migration file includes:

```python
# Migration metadata
revision = 'b6185fb1f227'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()

def downgrade() -> None:
    # Similar structure for rollbacks
```

### Column Ordering

The migration system automatically orders columns for consistency:

- `id` column: Always first
- Audit columns (`created_at`, `updated_at`): Always last
- Other columns: In model definition order

### Best Practices

1. **Always use `--autogenerate`** for detecting model changes
2. **Review generated migrations** before applying
3. **Use descriptive commit messages**
4. **Test migrations on staging** before production
5. **Keep migrations backward-compatible** when possible

## Connection Pooling

### PostgreSQL Pool Configuration

The application uses SQLAlchemy's connection pooling with these settings:

#### Pool Parameters
```python
POOL_SIZE: int = 5                    # Base pool size
POOL_MAX_OVERFLOW: int = 10          # Additional connections under load
POOL_TIMEOUT: int = 30               # Max time to wait for connection
POOL_RECYCLE: int = 300              # Connection lifetime (seconds)
POOL_PRE_PING: bool = False          # Test connection health
POOL_DISABLED: bool = False          # Disable pooling entirely
```

#### Pool Behavior
- **LIFO Pool Usage**: Reduces idle connections
- **Connection Recycling**: Prevents stale connections
- **Health Checking**: Optional pre-ping validation
- **Overflow Handling**: Dynamic scaling under load

### SQLite Pooling

SQLite uses simpler pooling due to its file-based nature:

```python
engine = create_async_engine(
    url=self.URL,
    pool_recycle=self.POOL_RECYCLE,
    pool_pre_ping=self.POOL_PRE_PING,
)
```

### Pool Monitoring

Monitor pool health through logging:

```python
# Enable pool logging
DATABASE_ECHO_POOL=true
SQLALCHEMY_LOG_LEVEL=10  # DEBUG level
```

## Database Testing

### Test Database Setup

The application uses pytest-databases for isolated test environments:

#### Configuration
```python
# tests/conftest.py
pytest_plugins = [
    "tests.data_fixtures",
    "pytest_databases.docker",
    "pytest_databases.docker.postgres",
]
```

#### Test Database Engine
```python
@pytest.fixture(name="engine")
async def fx_engine(postgres_service: PostgresService) -> AsyncEngine:
    return create_async_engine(
        URL(
            drivername="postgresql+asyncpg",
            username=postgres_service.user,
            password=postgres_service.password,
            host=postgres_service.host,
            port=postgres_service.port,
            database=postgres_service.database,
        ),
        echo=False,
        poolclass=NullPool,  # No pooling for tests
    )
```

### Database Seeding

Test databases are automatically seeded with fixtures:

```python
@pytest.fixture(autouse=True)
async def _seed_db(
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
    raw_users: list[User | dict[str, Any]],
) -> AsyncGenerator[None, None]:
    # Drop and recreate schema
    metadata = UUIDAuditBase.registry.metadata
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

    # Load fixtures and create test data
    async with RoleService.new(sessionmaker()) as service:
        fixture = await open_fixture_async(fixtures_path, "role")
        for obj in fixture:
            _ = await service.repository.get_or_upsert(match_fields="name", upsert=True, **obj)
```

### Test Configuration Files

Different environments use separate configurations:

- `.env.testing`: Minimal configuration for tests
- `.env.development`: Development database settings
- `.env.production`: Production-ready settings

## Multi-Environment Configuration

### Development Environment

```bash
# .env.development
DATABASE_URL=sqlite+aiosqlite:///db.sqlite3
DATABASE_ECHO=true
DATABASE_ECHO_POOL=true
DATABASE_POOL_SIZE=5
```

### Testing Environment

```bash
# .env.testing
DATABASE_URL=postgresql+asyncpg://app:app@127.0.0.1:15432/app
DATABASE_ECHO=false
DATABASE_ECHO_POOL=false
```

### Production Environment

```bash
# .env.production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/prod_db
DATABASE_ECHO=false
DATABASE_POOL_SIZE=20
DATABASE_MAX_POOL_OVERFLOW=30
DATABASE_POOL_TIMEOUT=60
DATABASE_POOL_RECYCLE=3600
DATABASE_PRE_POOL_PING=true
```

### Docker Integration

Local infrastructure uses Docker Compose:

```yaml
# deploy/docker-compose.infra.yml
services:
  db:
    image: postgres:latest
    ports:
      - "15432:5432"
    environment:
      POSTGRES_PASSWORD: "app"
      POSTGRES_USER: "app"
      POSTGRES_DB: "app"
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "app"]
      interval: 2s
      timeout: 3s
      retries: 40
```

#### Infrastructure Commands

```bash
# Start local database
make start-infra

# Stop infrastructure
make stop-infra

# Remove all data
make wipe-infra

# View logs
make infra-logs
```

## Performance & Optimization

### Connection Pool Optimization

#### Production Settings
```python
POOL_SIZE = 20                    # Base connections
POOL_MAX_OVERFLOW = 30            # Under load
POOL_TIMEOUT = 60                 # Wait time
POOL_RECYCLE = 3600              # 1 hour lifetime
POOL_PRE_PING = True             # Health checks
```

#### Monitoring
- Use `DATABASE_ECHO_POOL=true` for monitoring
- Monitor connection usage in logs
- Set up metrics collection

### Query Optimization

#### Indexing Strategy
The application uses strategic indexing:

```python
class User(UUIDAuditBase):
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    # Other fields...

class Todo(UUIDAuditBase):
    item: Mapped[str] = mapped_column(String(length=100), index=True, nullable=False)
    # Other fields...
```

#### Query Patterns
Use efficient query patterns:

```python
# Good: Use relationship loading
todos = await session.execute(
    select(Todo).options(selectinload(Todo.tags))
)

# Avoid: N+1 queries
for todo in todos:
    print(todo.tags)  # This causes N+1 queries
```

### Database Schema Optimization

#### UUID Primary Keys
All tables use UUID primary keys for:
- Global uniqueness
- Better security (no sequential IDs)
- Distributed system compatibility

#### Audit Fields
All tables include audit fields:
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp
- Automatically managed by Advanced Alchemy

## Backup & Recovery

### PostgreSQL Backup Strategies

#### Logical Backups
```bash
# Full database backup
pg_dump -h localhost -U app -d app > backup.sql

# Custom format backup (compressed)
pg_dump -h localhost -U app -d app -Fc > backup.dump

# Schema-only backup
pg_dump -h localhost -U app -d app -s > schema.sql
```

#### Physical Backups
```bash
# Using pg_basebackup for continuous backup
pg_basebackup -h localhost -D /backup/base -U app -v -P -W
```

#### Point-in-Time Recovery
```bash
# Restore to specific point
pg_ctl start -D /backup/base
psql -U app -d app -c "SELECT pg_restore_backup('timestamp');"
```

### SQLite Backup

```bash
# File-based backup
cp db.sqlite3 db.backup.sqlite3

# Using SQLite backup command
sqlite3 db.sqlite3 ".backup db.backup.sqlite3"
```

### Migration Safety

#### Safe Migration Practices

1. **Backup Before Migrations**:
   ```bash
   # Create backup before migration
   pg_dump app > pre_migration_backup.sql
   ```

2. **Test Migrations**:
   ```bash
   # Test migration on staging
   uv run app database upgrade --sql
   ```

3. **Rollback Plan**:
   ```bash
   # Know your rollback strategy
   uv run app database downgrade
   ```

#### Migration Rollback

```python
def downgrade() -> None:
    """Reversible migration operations."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()
```

## Troubleshooting

### Common Issues

#### Connection Errors

**Symptoms**: Connection timeouts, pool exhaustion

**Solutions**:
```python
# Increase pool settings
DATABASE_POOL_SIZE=10
DATABASE_MAX_POOL_OVERFLOW=20
DATABASE_POOL_TIMEOUT=60

# Enable connection validation
DATABASE_PRE_POOL_PING=true
```

**Debugging**:
```python
# Enable connection logging
DATABASE_ECHO=true
DATABASE_ECHO_POOL=true
SQLALCHEMY_LOG_LEVEL=10
```

#### Migration Failures

**Common Causes**:
- Database locked (SQLite)
- Permission issues
- Schema conflicts

**Solutions**:
```bash
# Check migration status
uv run app database current

# Force migration resolution
uv run app database stamp head

# Manual schema inspection
psql -U app -d app -c "\dt"
```

#### Performance Issues

**Symptoms**: Slow queries, high latency

**Diagnosis**:
```sql
-- Slow query analysis
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Index usage analysis
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'todo';
```

**Optimizations**:
```python
# Add missing indexes
op.create_index('ix_todo_user_created', 'todo', ['user_id', 'created_at'])

# Optimize queries
todos = await session.execute(
    select(Todo)
    .where(Todo.user_id == user_id)
    .order_by(Todo.created_at.desc())
    .limit(50)
)
```

### Debugging Tools

#### Database Connection Testing

```python
# Test database connectivity
async def test_connection():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(f"Connection successful: {result.scalar()}")
```

#### Migration Validation

```bash
# Validate migration files
uv run alembic check

# Compare model vs database
uv run alembic revision --autogenerate --sql
```

#### Performance Monitoring

```python
# Enable query logging
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
```

### Recovery Procedures

#### Database Corruption

**SQLite Recovery**:
```bash
# Check integrity
sqlite3 db.sqlite3 "PRAGMA integrity_check;"

# Recover data
sqlite3 db.sqlite3 ".recover" | sqlite3 recovered.db
```

**PostgreSQL Recovery**:
```bash
# Check database health
pg_isready -h localhost -p 5432

# Connection recovery
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';
```

#### Emergency Procedures

1. **Immediate Actions**:
   - Stop application
   - Create emergency backup
   - Assess damage scope

2. **Recovery Steps**:
   - Restore from recent backup
   - Apply transaction logs if available
   - Verify data integrity
   - Restart application with monitoring

3. **Post-Recovery**:
   - Investigate root cause
   - Update monitoring
   - Review backup strategy

## CLI Reference

### Database Commands

```bash
# Application management
uv run app database make-migrations    # Create migration
uv run app database upgrade            # Apply migrations
uv run app database downgrade          # Rollback migrations
uv run app database current            # Show current revision
uv run app database history            # Show migration history
uv run app database stamp              # Set revision without migration

# User management
uv run app user create                 # Create new user
uv run app user promote                # Promote to admin
uv run app user demote                 # Demote from admin
```

### Infrastructure Commands

```bash
# Docker infrastructure
make start-infra                       # Start local database
make stop-infra                        # Stop containers
make wipe-infra                        # Remove all data
make infra-logs                        # View container logs

# Application lifecycle
make dev                               # Development mode
make run                               # Production mode
make test                              # Run tests
make coverage                          # Test coverage report
```

---

This comprehensive database setup guide covers all aspects of database management for the Litestar Todo application. For specific implementation details, refer to the source code in the respective directories mentioned throughout this document.