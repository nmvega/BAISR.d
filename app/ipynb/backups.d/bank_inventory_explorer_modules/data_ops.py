"""
Data loading, caching, and transformation operations.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


class DataManager:
    """
    Manages data loading, caching, and preparation for display.
    """
    
    def __init__(self, database_connection):
        """
        Initialize data manager.
        
        Args:
            database_connection: DatabaseConnection instance
        """
        self.db = database_connection
        self.cache = {}
        logger.debug("DataManager initialized")
    
    def clear_cache(self, schema_only=False):
        """
        Clear cached data.
        
        Args:
            schema_only (bool): If True, only clear data for current schema
        """
        if schema_only:
            schema = self.db.current_schema
            self.cache[schema] = {}
            logger.info(f"Cleared cache for {schema} schema")
        else:
            self.cache = {}
            logger.info("Cleared all cached data")
    
    def load_components(self):
        """
        Load components data with relationship counts.

        Returns:
            pd.DataFrame: Components with relationship counts
        """
        query = """
        SELECT
            c.*,
            ct.type_name as component_type,
            cs.subtype_name as component_subtype,
            ce.environment_name as environment,
            cpl.location_name as physical_location,
            cos.status_name as ops_status,
            cal.level_name as abstraction_level,
            cp.protocol_name as protocol_name,
            c.app_code,
            c.mac,
            c.record_quality_grade,
            c.created_at,
            c.created_by,
            c.updated_at,
            c.updated_by,
            COALESCE(rels_from.from_count, 0) as relationship_from_count,
            COALESCE(rels_to.to_count, 0) as relationship_to_count,
            (
                COALESCE(rels_from.from_count, 0) +
                COALESCE(rels_to.to_count, 0)
            ) as total_relationship_count
        FROM {{SCHEMA}}.biz_components c
        LEFT JOIN {{SCHEMA}}.component_types ct ON c.component_type_id = ct.component_type_id
        LEFT JOIN {{SCHEMA}}.component_subtypes cs ON c.component_subtype_id = cs.component_subtype_id
        LEFT JOIN {{SCHEMA}}.component_environments ce ON c.environment_id = ce.environment_id
        LEFT JOIN {{SCHEMA}}.component_physical_locations cpl ON c.physical_location_id = cpl.physical_location_id
        LEFT JOIN {{SCHEMA}}.component_ops_statuses cos ON c.ops_status_id = cos.ops_status_id
        LEFT JOIN {{SCHEMA}}.component_abstraction_levels cal ON c.abstraction_level_id = cal.abstraction_level_id
        LEFT JOIN {{SCHEMA}}.component_protocols cp ON c.protocol_id = cp.protocol_id
        LEFT JOIN (
            SELECT component_id, COUNT(*) as from_count
            FROM {{SCHEMA}}.biz_component_relationships
            GROUP BY component_id
        ) rels_from ON c.component_id = rels_from.component_id
        LEFT JOIN (
            SELECT related_component_id, COUNT(*) as to_count
            FROM {{SCHEMA}}.biz_component_relationships
            GROUP BY related_component_id
        ) rels_to ON c.component_id = rels_to.related_component_id
        ORDER BY c.fqdn;
        """
        
        logger.info(f"Loading components from {self.db.current_schema} schema...")
        df = self.db.get_dataframe(query)
        logger.info(f"✓ Loaded {len(df)} components")
        return df
    
    # REMOVED: Dependencies tab - redundant with relationships for single-table schema
    # def load_dependencies(self):
    #     """
    #     Load component dependencies (relationships of type 'persists_to', 'consumes_api_from', etc).
    #     
    #     Returns:
    #         pd.DataFrame: Dependencies with component names
    #     """
    #     query = """
    #     SELECT 
    #         r.*,
    #         rt.type_name as relationship_type,
    #         c1.fqdn as source_name,
    #         ct1.type_name as source_type,
    #         cpl1.location_name as source_location,
    #         c2.fqdn as target_name,
    #         ct2.type_name as target_type,
    #         cpl2.location_name as target_location
    #     FROM {{SCHEMA}}.biz_component_relationships r
    #     JOIN {{SCHEMA}}.component_relationship_types rt ON r.relationship_type_id = rt.relationship_type_id
    #     JOIN {{SCHEMA}}.biz_components c1 ON r.component_id = c1.component_id
    #     JOIN {{SCHEMA}}.biz_components c2 ON r.related_component_id = c2.component_id
    #     LEFT JOIN {{SCHEMA}}.component_types ct1 ON c1.component_type_id = ct1.component_type_id
    #     LEFT JOIN {{SCHEMA}}.component_types ct2 ON c2.component_type_id = ct2.component_type_id
    #     LEFT JOIN {{SCHEMA}}.component_physical_locations cpl1 ON c1.physical_location_id = cpl1.physical_location_id
    #     LEFT JOIN {{SCHEMA}}.component_physical_locations cpl2 ON c2.physical_location_id = cpl2.physical_location_id
    #     WHERE rt.type_name IN ('persists_to', 'consumes_api_from', 'subscribes_to', 'publishes_to', 'caches_from')
    #     ORDER BY c1.fqdn, c2.fqdn;
    #     """
    #     
    #     logger.info(f"Loading dependencies from {self.db.current_schema} schema...")
    #     df = self.db.get_dataframe(query)
    #     logger.info(f"✓ Loaded {len(df)} dependencies")
    #     return df
    
    def load_relationships(self):
        """
        Load all relationships (including failover, replication, etc).
        
        Returns:
            pd.DataFrame: All relationships with component names
        """
        query = """
        SELECT 
            r.*,
            rt.type_name as relationship_type,
            c1.fqdn as component1_name,
            ct1.type_name as component1_type,
            cpl1.location_name as component1_location,
            c2.fqdn as component2_name,
            ct2.type_name as component2_type,
            cpl2.location_name as component2_location
        FROM {{SCHEMA}}.biz_component_relationships r
        JOIN {{SCHEMA}}.component_relationship_types rt ON r.relationship_type_id = rt.relationship_type_id
        JOIN {{SCHEMA}}.biz_components c1 ON r.component_id = c1.component_id
        JOIN {{SCHEMA}}.biz_components c2 ON r.related_component_id = c2.component_id
        LEFT JOIN {{SCHEMA}}.component_types ct1 ON c1.component_type_id = ct1.component_type_id
        LEFT JOIN {{SCHEMA}}.component_types ct2 ON c2.component_type_id = ct2.component_type_id
        LEFT JOIN {{SCHEMA}}.component_physical_locations cpl1 ON c1.physical_location_id = cpl1.physical_location_id
        LEFT JOIN {{SCHEMA}}.component_physical_locations cpl2 ON c2.physical_location_id = cpl2.physical_location_id
        ORDER BY c1.fqdn, c2.fqdn;
        """
        
        logger.info(f"Loading relationships from {self.db.current_schema} schema...")
        df = self.db.get_dataframe(query)
        logger.info(f"✓ Loaded {len(df)} peer relationships")
        return df
    
    def refresh_all_data(self):
        """
        Refresh all data from database.
        
        Returns:
            dict: Dictionary with 'components', 'dependencies', 'relationships' DataFrames
        """
        logger.info(f"Refreshing all data from {self.db.current_schema} schema...")
        
        # Clear cache for current schema
        self.clear_cache(schema_only=True)
        
        # Load fresh data
        schema = self.db.current_schema
        if schema not in self.cache:
            self.cache[schema] = {}
        
        self.cache[schema]['components'] = self.load_components()
        # REMOVED: Dependencies redundant with relationships for single-table schema
        # self.cache[schema]['dependencies'] = self.load_dependencies()
        self.cache[schema]['relationships'] = self.load_relationships()
        
        # Log summary
        logger.info("Data refresh complete:")
        for key, df in self.cache[schema].items():
            logger.info(f"  - {key}: {len(df)} rows")
        
        return self.cache[schema]
    
    def get_cached_data(self):
        """
        Get cached data for current schema.
        
        Returns:
            dict: Cached DataFrames or empty dict if not cached
        """
        schema = self.db.current_schema
        if schema in self.cache:
            return self.cache[schema]
        return {}


def format_quality_grade(grade):
    """Convert quality grade to visual indicator."""
    indicators = {
        '_PT_GREEN_RECORD_': '🟢',
        '_PT_YELLOW_RECORD_': '🟡',
        '_PT_RED_RECORD_': '🔴'
    }
    return indicators.get(grade, '⚫')


def prepare_table_displays(data, show_audit=False):
    """
    Prepare data for table display.

    Args:
        data (dict): Dictionary with DataFrames
        show_audit (bool): Whether to include audit columns

    Returns:
        dict: Prepared DataFrames for display
    """
    display_tables = {}

    # Components table
    if 'components' in data and not data['components'].empty:
        components_df = data['components'].copy()

        # Format quality grade
        if 'record_quality_grade' in components_df.columns:
            components_df['quality_indicator'] = components_df['record_quality_grade'].apply(format_quality_grade)

        # Define column mappings - corrected to match actual schema
        column_mapping = {
            'quality_indicator': 'Quality',
            'fqdn': 'FQDN',
            'app_code': 'App Code',
            'component_type': 'Type',
            'component_subtype': 'Subtype',
            'ip': 'IP Address',
            'vlan': 'VLAN',
            'port': 'Port',
            'mac': 'MAC Address',
            'protocol_name': 'Protocol',
            'physical_location': 'Location',
            'ops_status': 'Status',
            'environment': 'Environment',
            'abstraction_level': 'Abstraction',
            'total_relationship_count': 'Connections'
        }

        # Add audit columns if requested
        if show_audit:
            column_mapping.update({
                'created_at': 'Created At',
                'created_by': 'Created By',
                'updated_at': 'Updated At',
                'updated_by': 'Updated By'
            })

        # Build display dataframe with available columns
        display_cols = {}
        for db_col, display_name in column_mapping.items():
            if db_col in components_df.columns:
                display_cols[display_name] = components_df[db_col]

        if display_cols:
            components_display = pd.DataFrame(display_cols)
            display_tables['components'] = components_display
            logger.debug(f"Prepared components display: {components_display.shape}")
    
    # REMOVED: Dependencies table - redundant with relationships for single-table schema
    # if 'dependencies' in data and not data['dependencies'].empty:
    #     dependencies_df = data['dependencies']
    #     # Use our column names
    #     display_cols = {}
    #     if 'source_name' in dependencies_df.columns:
    #         display_cols['source'] = dependencies_df['source_name']
    #     if 'source_type' in dependencies_df.columns:
    #         display_cols['source_type'] = dependencies_df['source_type']
    #     if 'source_location' in dependencies_df.columns:
    #         display_cols['source_location'] = dependencies_df['source_location']
    #     if 'relationship_type' in dependencies_df.columns:
    #         display_cols['relationship'] = dependencies_df['relationship_type']
    #     if 'target_name' in dependencies_df.columns:
    #         display_cols['target'] = dependencies_df['target_name']
    #     if 'target_type' in dependencies_df.columns:
    #         display_cols['target_type'] = dependencies_df['target_type']
    #     if 'target_location' in dependencies_df.columns:
    #         display_cols['target_location'] = dependencies_df['target_location']
    #     
    #     if display_cols:
    #         dependencies_display = pd.DataFrame(display_cols)
    #         display_tables['dependencies'] = dependencies_display
    #         logger.debug(f"Prepared dependencies display: {dependencies_display.shape}")
    
    # Relationships table (all relationships)
    if 'relationships' in data and not data['relationships'].empty:
        relationships_df = data['relationships'].copy()

        # Define column mappings with proper names
        rel_column_mapping = {
            'component1_name': 'Component 1',
            'component1_type': 'Component 1 Type',
            'component1_location': 'Component 1 Location',
            'relationship_type': 'Relationship',
            'component2_name': 'Component 2',
            'component2_type': 'Component 2 Type',
            'component2_location': 'Component 2 Location',
            'description': 'Description'
        }

        # Add audit columns if requested
        if show_audit:
            rel_column_mapping.update({
                'created_at': 'Created At',
                'created_by': 'Created By',
                'updated_at': 'Updated At',
                'updated_by': 'Updated By'
            })

        # Build display dataframe with available columns
        display_cols = {}
        for db_col, display_name in rel_column_mapping.items():
            if db_col in relationships_df.columns:
                display_cols[display_name] = relationships_df[db_col]

        if display_cols:
            relationships_display = pd.DataFrame(display_cols)
            display_tables['relationships'] = relationships_display
            logger.debug(f"Prepared relationships display: {relationships_display.shape}")

    return display_tables