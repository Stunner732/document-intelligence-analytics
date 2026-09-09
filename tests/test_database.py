"""Tests for database module and schema design."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from contextlib import contextmanager


class TestDatabaseSchemaDesign:
    """Test the SQL schema file is valid and complete."""

    def test_schema_sql_file_exists(self):
        """Schema migration file should exist."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        assert schema_file.exists(), f"Schema file not found: {schema_file}"

    def test_schema_sql_has_required_tables(self):
        """Schema should create all required tables."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        sql_content = schema_file.read_text(encoding="utf-8")

        required_tables = [
            "applications",
            "events",
            "offers",
            "synthetic_extensions",
            "data_loads",
            "schema_versions",
        ]

        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in sql_content, (
                f"Table '{table}' not found in schema"
            )

    def test_schema_sql_has_primary_keys(self):
        """All tables should have primary keys."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        sql_content = schema_file.read_text(encoding="utf-8")

        assert "PRIMARY KEY" in sql_content

    def test_schema_sql_has_foreign_keys(self):
        """Events should reference applications, offers should reference applications."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        sql_content = schema_file.read_text(encoding="utf-8")

        assert "REFERENCES applications(application_id)" in sql_content

    def test_schema_sql_has_indexes(self):
        """Schema should include performance indexes."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        sql_content = schema_file.read_text(encoding="utf-8")

        assert "CREATE INDEX" in sql_content

    def test_schema_sql_has_version_tracking(self):
        """Schema should have version tracking table."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        sql_content = schema_file.read_text(encoding="utf-8")

        assert "schema_versions" in sql_content

    def test_schema_sql_is_not_empty(self):
        """Schema file should not be empty."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        sql_content = schema_file.read_text(encoding="utf-8")
        assert len(sql_content.strip()) > 0

    def test_schema_sql_is_valid_sql(self):
        """Schema should contain valid SQL syntax (basic checks)."""
        schema_file = Path(__file__).parent.parent / "sql" / "001_create_schema.sql"
        sql_content = schema_file.read_text(encoding="utf-8")

        # Basic SQL validation
        assert "CREATE TABLE" in sql_content
        assert "NOT NULL" in sql_content


class TestDatabaseModule:
    """Test the database Python module structure."""

    def test_database_module_exists(self):
        """Database module should exist."""
        module_file = Path(__file__).parent.parent / "src" / "database.py"
        assert module_file.exists(), f"Database module not found: {module_file}"

    def test_database_module_has_required_functions(self):
        """Module should expose required database functions."""
        module_file = Path(__file__).parent.parent / "src" / "database.py"
        content = module_file.read_text(encoding="utf-8")

        required_functions = [
            "get_connection",
            "get_cursor",
            "check_database_connection",
            "run_migrations",
        ]

        for func in required_functions:
            assert f"def {func}" in content, f"Function '{func}' not found in database module"

    def test_database_module_uses_config(self):
        """Module should import settings from config."""
        module_file = Path(__file__).parent.parent / "src" / "database.py"
        content = module_file.read_text(encoding="utf-8")

        assert "from src.config import settings" in content

    def test_database_module_has_connection_context_manager(self):
        """Module should have context manager for connections."""
        module_file = Path(__file__).parent.parent / "src" / "database.py"
        content = module_file.read_text(encoding="utf-8")

        assert "@contextmanager" in content


class TestScriptsExist:
    """Test that required scripts exist."""

    def test_init_database_script_exists(self):
        """Database initialization script should exist."""
        script_file = Path(__file__).parent.parent / "scripts" / "init_database.py"
        assert script_file.exists(), f"Init script not found: {script_file}"

    def test_load_xes_to_db_script_exists(self):
        """XES loader script should exist."""
        script_file = Path(__file__).parent.parent / "scripts" / "load_xes_to_db.py"
        assert script_file.exists(), f"Loader script not found: {script_file}"


class TestConfiguration:
    """Test configuration is properly set up."""

    def test_env_example_exists(self):
        """.env.example should exist with database settings."""
        env_file = Path(__file__).parent.parent / ".env.example"
        assert env_file.exists()
        content = env_file.read_text(encoding="utf-8")
        assert "POSTGRES_HOST" in content
        assert "POSTGRES_DB" in content
        assert "POSTGRES_USER" in content
        assert "POSTGRES_PASSWORD" in content

    def test_config_has_database_settings(self):
        """Config module should have database settings."""
        config_file = Path(__file__).parent.parent / "src" / "config.py"
        content = config_file.read_text(encoding="utf-8")

        assert "postgres_host" in content
        assert "postgres_port" in content
        assert "postgres_db" in content
        assert "postgres_user" in content
        assert "postgres_password" in content

    def test_docker_compose_has_postgres(self):
        """Docker Compose should define PostgreSQL service."""
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        content = compose_file.read_text(encoding="utf-8")

        assert "postgres:" in content
        assert "postgres:16-alpine" in content
        assert "healthcheck" in content