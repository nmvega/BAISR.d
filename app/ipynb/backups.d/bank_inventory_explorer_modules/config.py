"""
Configuration and environment variable handling.
"""

import os
import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Component color palette - mapped to our component_types
COMPONENT_COLORS = {
    'Application':             '#2E7D32',  # Forest green - applications
    'Database':                '#1565C0',  # Deep blue - databases  
    'Cache':                   '#B71C1C',  # Deep red - caching layer
    'MessageQueue':            '#6A1B9A',  # Purple - message queues
    'Storage':                 '#263238',  # Blue grey - storage systems
    'LoadBalancer':            '#4A148C',  # Deep purple - load balancers
    'Network':                 '#004D40',  # Teal - network components
    # Legacy mappings for compatibility
    'application':             '#2E7D32',
    'polyglot_persistence':    '#1565C0',  
    'block_level_persistence': '#263238',
    'networking':              '#004D40'
}

# Find project root
def find_project_root():
    """Find the project root directory."""
    current = Path(__file__).parent
    while current != current.parent:
        if (current / '.env').exists():
            return current
        current = current.parent
    return Path.cwd()

PROJECT_ROOT = find_project_root()

# Load environment variables
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"✓ Environment loaded from: {env_path}")
else:
    logger.warning(f"⚠️ No .env file found at: {env_path}")


def load_yaml_config(config_name):
    """
    Load a YAML configuration file from app/configs/.
    
    Args:
        config_name (str): Name of config file (without .yaml extension)
        
    Returns:
        dict: Configuration dictionary
    """
    config_path = PROJECT_ROOT / 'app' / 'configs' / f'{config_name}.yaml'
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            logger.debug(f"Loaded config: {config_name}")
            return config or {}
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading config {config_name}: {e}")
        return {}


def get_config(key_path):
    """
    Get configuration value using dot notation.
    
    Args:
        key_path (str): Dot-separated path (e.g., 'database.pool_size' or 'env.POSTGRESQL_BAIS_DB_ADMIN_URL')
        
    Returns:
        Any: Configuration value or None if not found
    """
    parts = key_path.split('.')
    
    # Handle environment variables
    if parts[0] == 'env':
        if len(parts) == 2:
            value = os.getenv(parts[1])
            if value:
                logger.debug(f"Retrieved env var: {parts[1]}")
            return value
        return None
    
    # Handle YAML configs
    config_file = parts[0]
    config = load_yaml_config(config_file)
    
    # Navigate through nested dictionary
    result = config
    for part in parts[1:]:
        if isinstance(result, dict) and part in result:
            result = result[part]
        else:
            logger.debug(f"Config key not found: {key_path}")
            return None
    
    return result


def get_component_colors():
    """
    Get the component color palette.
    
    Returns:
        dict: Component type to color mapping
    """
    return COMPONENT_COLORS.copy()


def get_database_config():
    """
    Get database configuration.
    
    Returns:
        dict: Database configuration
    """
    return {
        'url': os.getenv('POSTGRESQL_BAIS_DB_ADMIN_URL'),
        'supabase_url': os.getenv('SUPABASE_URL'),
        'supabase_key': os.getenv('SUPABASE_ANON_KEY'),
        'schema': 'demo'  # Default schema
    }


def get_app_config():
    """
    Get application configuration.
    
    Returns:
        dict: Application configuration
    """
    app_config = load_yaml_config('app')
    return app_config or {
        'name': 'Bank Application Inventory System',
        'version': '3.0.0'
    }
