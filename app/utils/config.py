"""
BAIS Configuration Management Module
====================================
Simple, direct configuration loading from .env and YAML files.
NO OVER-ENGINEERING - Just straightforward config access.

Usage:
    from utils.config import Config
    config = Config()
    db_url = config.get_db_url('admin')
    cookie_name = config.get('auth.cookie.name')
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Optional


class Config:
    """
    Simple configuration manager for BAIS application.
    Loads settings from .env and app.yaml files.
    """
    
    def __init__(self, env_path: Optional[Path] = None, yaml_path: Optional[Path] = None):
        """
        Initialize configuration by loading .env and YAML files.
        
        Args:
            env_path: Path to .env file (defaults to project root)
            yaml_path: Path to YAML config (defaults to app/configs/app.yaml)
        """
        # Determine paths
        if env_path is None:
            # Navigate from app/utils to project root
            env_path = Path(__file__).parent.parent.parent / '.env'
        
        if yaml_path is None:
            yaml_path = Path(__file__).parent.parent / 'configs' / 'app.yaml'
        
        # Load .env file
        load_dotenv(env_path)
        
        # Load YAML configuration
        self.yaml_config = {}
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                self.yaml_config = yaml.safe_load(f) or {}
        else:
            print(f"Warning: Configuration file not found at {yaml_path}")
    
    def get_db_url(self, user_type: str = 'admin') -> Optional[str]:
        """
        Get database connection URL for specified user type.
        
        Args:
            user_type: One of 'admin', 'ro' (read-only), 'rw' (read-write)
            
        Returns:
            Database connection URL string or None if not found
        """
        # Simple, direct mapping - no complex patterns
        url_mapping = {
            'admin': 'POSTGRESQL_BAIS_DB_ADMIN_URL',
            'ro': 'POSTGRESQL_BAIS_DB_RO_URL',
            'rw': 'POSTGRESQL_BAIS_DB_RW_URL',
            'root': 'POSTGRESQL_ROOT_URL'
        }
        
        env_var = url_mapping.get(user_type)
        if env_var:
            return os.getenv(env_var)
        
        return None
    
    def get_db_config(self) -> dict:
        """
        Get database configuration details.
        
        Returns:
            Dictionary with database configuration
        """
        return {
            'host': os.getenv('POSTGRESQL_INSTANCE_HOST', 'localhost'),
            'port': os.getenv('POSTGRESQL_INSTANCE_PORT', '5432'),
            'database': os.getenv('POSTGRESQL_BAIS_DB', 'prutech_bais'),
            'schemas': self.get('database.available_schemas', ['demo']),
            'default_schema': self.get('database.default_schema', 'demo')
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path like 'auth.cookie.name'
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Examples:
            >>> config.get('ui.app_title')
            'Bank Application Inventory System (BAIS)'
            >>> config.get('auth.cookie.expiry_hours', 2)
            2
        """
        # Check environment variables first (for secrets)
        env_value = os.getenv(key_path.upper().replace('.', '_'))
        if env_value is not None:
            return env_value
        
        # Navigate through YAML config using dot notation
        keys = key_path.split('.')
        value = self.yaml_config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    break
            else:
                value = None
                break
        
        # Special handling for cookie key (from env)
        if key_path == 'auth.cookie.key':
            key_env_var = self.get('auth.cookie.key_env_var', 'AUTH_COOKIE_KEY')
            return os.getenv(key_env_var, default)
        
        return value if value is not None else default
    
    def get_all_db_urls(self) -> dict:
        """
        Get all database URLs for different user types.
        
        Returns:
            Dictionary mapping user types to connection URLs
        """
        return {
            'admin': self.get_db_url('admin'),
            'ro': self.get_db_url('ro'),
            'rw': self.get_db_url('rw'),
            'root': self.get_db_url('root')
        }
    
    def get_ui_colors(self) -> dict:
        """
        Get UI color configuration.
        
        Returns:
            Dictionary of color settings
        """
        return self.get('ui.colors', {})
    
    def get_auth_config(self) -> dict:
        """
        Get authentication configuration.
        
        Returns:
            Dictionary with auth settings
        """
        return {
            'require_auth': self.get('auth.require_auth', True),
            'cookie_name': self.get('auth.cookie.name', 'bais_auth'),
            'cookie_key': self.get('auth.cookie.key'),  # From env
            'expiry_hours': self.get('auth.cookie.expiry_hours', 2),
            'allow_registration': self.get('auth.allow_registration', False)
        }
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            True if feature is enabled, False otherwise
        """
        return self.get(f'features.{feature_name}', False)
    
    def get_logging_config(self) -> dict:
        """
        Get logging configuration.
        
        Returns:
            Dictionary with logging settings
        """
        return self.get('logging', {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        })


# Singleton instance for easy import
_config = None

def get_config() -> Config:
    """
    Get singleton configuration instance.
    
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


# For convenience, allow direct import
if __name__ != "__main__":
    config = get_config()