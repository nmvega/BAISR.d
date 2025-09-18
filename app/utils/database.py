"""
BAIS Database Utilities Module
===============================
Simple database connection and query management.
NO ORM - Direct psycopg2 for clarity and control.

Usage:
    from utils.database import Database
    db = Database()
    results = db.fetch_all("SELECT * FROM biz_components")
"""

import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
from .config import get_config
from .app_logger import get_logger, log_database_operation


class Database:
    """
    Simple database manager for BAIS application.
    Uses psycopg2 directly - no ORM complexity.
    """
    
    def __init__(self, user_type: str = 'ro', schema: str = None):
        """
        Initialize database connection manager.
        
        Args:
            user_type: Type of database user ('admin', 'ro', 'rw', 'root')
            schema: Default schema to use (if not specified, uses config default)
        """
        self.config = get_config()
        self.logger = get_logger(self.__class__.__name__)
        self.user_type = user_type
        
        # Get connection URL
        self.connection_url = self.config.get_db_url(user_type)
        if not self.connection_url:
            raise ValueError(f"No database URL found for user type: {user_type}")
        
        # Set default schema
        if schema is None:
            schema = self.config.get('database.default_schema', 'demo')
        self.current_schema = schema
        
        self.logger.info(f"Database initialized for user '{user_type}' with schema '{schema}'")
    
    @contextmanager
    def get_connection(self, autocommit: bool = False):
        """
        Context manager for database connections.
        Simple, clean connection handling.
        
        Args:
            autocommit: Whether to autocommit transactions
            
        Yields:
            psycopg2 connection object
            
        Example:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM biz_components")
        """
        conn = None
        try:
            conn = psycopg2.connect(self.connection_url)
            
            if autocommit:
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            # Set search path to current schema
            if self.current_schema:
                with conn.cursor() as cur:
                    # Safely set schema using psycopg2's SQL composition
                    cur.execute(
                        "SET search_path TO %s, public",
                        (self.current_schema,)
                    )
                    log_database_operation(f"Set search_path to {self.current_schema}", self.current_schema)
            
            yield conn
            
            if not autocommit:
                conn.commit()
                
        except psycopg2.Error as e:
            if conn and not autocommit:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def set_schema(self, schema: str):
        """
        Change the current working schema.
        
        Args:
            schema: Schema name to switch to
        """
        available_schemas = self.config.get('database.available_schemas', [])
        if schema not in available_schemas:
            raise ValueError(f"Schema '{schema}' not in available schemas: {available_schemas}")
        
        self.current_schema = schema
        self.logger.info(f"Switched to schema: {schema}")
    
    def fetch_all(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """
        Execute query and return all results as list of dicts.
        
        Args:
            query: SQL query to execute
            params: Query parameters (prevents SQL injection)
            
        Returns:
            List of dictionaries with query results
            
        Example:
            components = db.fetch_all(
                "SELECT * FROM biz_components WHERE environment_id = %s",
                (1,)
            )
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Convert to regular dicts
                return [dict(row) for row in results]
    
    def fetch_one(self, query: str, params: Tuple = None) -> Optional[Dict[str, Any]]:
        """
        Execute query and return first result as dict.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Dictionary with first row or None if no results
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                return dict(result) if result else None
    
    def execute(self, query: str, params: Tuple = None) -> int:
        """
        Execute a query that modifies data (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Number of affected rows
            
        Example:
            rows_updated = db.execute(
                "UPDATE biz_components SET operational_status_id = %s WHERE component_id = %s",
                (2, 100)
            )
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                affected_rows = cur.rowcount
                log_database_operation(
                    f"Executed query affecting {affected_rows} rows",
                    self.current_schema
                )
                return affected_rows
    
    def insert_returning(self, query: str, params: Tuple = None) -> Optional[Dict[str, Any]]:
        """
        Execute INSERT query with RETURNING clause.
        
        Args:
            query: INSERT query with RETURNING clause
            params: Query parameters
            
        Returns:
            Dictionary with returned row data
            
        Example:
            new_component = db.insert_returning(
                "INSERT INTO biz_components (component_name, component_type_id, component_subtype_id, 
                                           component_abstraction_level_id, operational_status_id, 
                                           environment_id, physical_location_id, created_by, updated_by) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
                ('web-server', 1, 1, 1, 1, 1, 1, 'user123', 'user123')
            )
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                if result:
                    log_database_operation(f"Inserted new record", self.current_schema)
                return dict(result) if result else None
    
    def bulk_insert(self, table: str, records: List[Dict[str, Any]]) -> int:
        """
        Bulk insert multiple records efficiently.
        
        Args:
            table: Table name
            records: List of dictionaries to insert
            
        Returns:
            Number of inserted records
            
        Example:
            components = [
                {'component_name': 'web1', 'fqdn': 'web1.bank.com', ...},
                {'component_name': 'web2', 'fqdn': 'web2.bank.com', ...}
            ]
            count = db.bulk_insert('biz_components', components)
        """
        if not records:
            return 0
        
        # Get column names from first record
        columns = list(records[0].keys())
        
        # Build INSERT query
        placeholders = ','.join(['%s'] * len(columns))
        columns_str = ','.join(columns)
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Convert records to tuples
                values = [tuple(record[col] for col in columns) for record in records]
                
                # Use execute_batch for efficiency
                psycopg2.extras.execute_batch(cur, query, values)
                inserted = len(values)
                log_database_operation(f"Bulk inserted {inserted} records into {table}", self.current_schema)
                return inserted
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the current schema.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = %s
            )
        """
        result = self.fetch_one(query, (self.current_schema, table_name))
        return result['exists'] if result else False
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = %s
            ORDER BY ordinal_position
        """
        return self.fetch_all(query, (self.current_schema, table_name))
    
    def get_reference_data(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get all records from a reference table (ref_component_types, ref_component_environments, etc.).
        
        Args:
            table_name: Name of the reference table
            
        Returns:
            List of all records in the table
        """
        # Validate it's a reference table for safety
        valid_ref_tables = [
            'ref_component_types', 'ref_component_operational_statuses', 'ref_component_environments',
            'ref_component_physical_locations', 'ref_component_relationship_types', 'auth_user_roles'
        ]
        
        if table_name not in valid_ref_tables:
            raise ValueError(f"'{table_name}' is not a valid reference table")
        
        return self.fetch_all(f"SELECT * FROM {table_name} ORDER BY 1")
    
    def test_connection(self) -> bool:
        """
        Test if database connection works.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    success = result[0] == 1
                    if success:
                        self.logger.info(f"Connection test successful for {self.user_type} user")
                    return success
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False


class DatabasePool:
    """
    Simple connection pool manager for multiple user types.
    Maintains separate connections for different permission levels.
    """
    
    def __init__(self):
        """Initialize connection pool with different user types."""
        self.connections = {}
        self.config = get_config()
        self.logger = get_logger(self.__class__.__name__)
    
    def get_database(self, user_type: str = 'ro', schema: str = None) -> Database:
        """
        Get or create a database connection for specified user type.
        
        Args:
            user_type: Type of database user ('admin', 'ro', 'rw')
            schema: Schema to use
            
        Returns:
            Database instance
        """
        key = f"{user_type}:{schema or 'default'}"
        
        if key not in self.connections:
            self.connections[key] = Database(user_type, schema)
            self.logger.debug(f"Created new database connection: {key}")
        
        return self.connections[key]
    
    def close_all(self):
        """Close all connections in the pool."""
        self.connections.clear()
        self.logger.info("Closed all database connections")


# Global pool instance for convenience
_pool = DatabasePool()

def get_database(user_type: str = 'ro', schema: str = None) -> Database:
    """
    Get a database connection from the global pool.
    
    Args:
        user_type: Type of database user
        schema: Schema to use
        
    Returns:
        Database instance
    """
    return _pool.get_database(user_type, schema)