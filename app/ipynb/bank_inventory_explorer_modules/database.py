"""
Database connection management with schema awareness.
"""

import os
import logging
import psycopg2
import psycopg2.extras
import pandas as pd

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Manages PostgreSQL database connections with schema switching capability.
    Supports both 'demo' and 'public' (live) schemas.
    """
    
    def __init__(self):
        """Initialize database connection manager."""
        self.connection = None
        self.current_schema = 'demo'
        logger.debug("DatabaseConnection initialized")
    
    def connect(self):
        """
        Establish database connection using POSTGRESQL_BAIS_DB_ADMIN_URL from environment.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            db_url = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_URL')
            if not db_url:
                logger.error("POSTGRESQL_BAIS_DB_ADMIN_URL not found in environment")
                return False
            
            logger.debug(f"Connecting to database (URL length: {len(db_url)} chars)")
            
            self.connection = psycopg2.connect(
                db_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            
            logger.info("✓ Database connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def set_schema(self, schema_name):
        """
        Set the current schema for queries.
        
        Args:
            schema_name (str): 'demo' or 'public' (live)
        """
        if schema_name not in ['demo', 'public']:
            logger.warning(f"Invalid schema name: {schema_name}, using 'demo'")
            schema_name = 'demo'
        
        self.current_schema = schema_name
        logger.info(f"Schema set to: {schema_name}")
    
    def execute_query(self, query, params=None):
        """
        Execute a query with schema placeholder replacement.
        
        Args:
            query (str): SQL query with {{SCHEMA}} placeholder
            params (tuple): Query parameters
            
        Returns:
            list: Query results as list of dictionaries
        """
        if not self.connection:
            logger.error("No database connection available")
            return None
        
        try:
            with self.connection.cursor() as cursor:
                # Replace schema placeholder
                formatted_query = query.replace('{{SCHEMA}}', self.current_schema)
                logger.debug(f"Executing query on schema: {self.current_schema}")
                
                cursor.execute(formatted_query, params)
                results = cursor.fetchall()
                
                logger.debug(f"Query returned {len(results) if results else 0} rows")
                return results
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return None
    
    def get_dataframe(self, query, params=None):
        """
        Execute query and return results as pandas DataFrame.
        
        Args:
            query (str): SQL query with {{SCHEMA}} placeholder
            params (tuple): Query parameters
            
        Returns:
            pd.DataFrame: Query results as DataFrame
        """
        results = self.execute_query(query, params)
        
        if results is None:
            logger.warning("Query returned None, returning empty DataFrame")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        logger.debug(f"Created DataFrame with shape: {df.shape}")
        return df
    
    def test_connection(self):
        """
        Test the database connection.
        
        Returns:
            bool: True if connection is active
        """
        if not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except:
            return False
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()