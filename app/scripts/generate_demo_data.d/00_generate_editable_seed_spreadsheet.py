#!/usr/bin/env python3
"""
Generate Demo Data Excel Spreadsheet for BAIS Database - Consulting Storytelling Tool (v3)
Creates realistic bank infrastructure demo data with intentional problems for visualization.

This generator creates data that tells a story about network segmentation issues,
making it easy for consultants to demonstrate problems and justify recommendations.

Version 3 Features:
- Enhanced help system with --verbose-help for detailed explanations
- Supports pending discovery simulation with --pending-ratio parameter
- Can generate components with incomplete data (_PT_PENDING_ placeholders)
- Demonstrates data quality workflow with GREEN/YELLOW/RED record grades
- Intentionally overrides schema defaults for complete records with meaningful values
- Allows schema defaults (auto-generated FQDNs) for pending discovery records
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import xlsxwriter
import random
from typing import Dict, List, Tuple, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import argparse
import hashlib


class DemoDataGenerator:
    """Generate demo data Excel spreadsheet for BAIS consulting demonstrations."""
    
    def __init__(self, connection_string: str, schema: str, output_dir: str,
                 scale: str = 'medium', problem_ratio: float = 0.3,
                 app_concentration: str = 'medium', seed: Optional[int] = None,
                 pending_ratio: float = 0.0):
        """
        Initialize the generator with parameters for controlling data generation.

        Args:
            connection_string: PostgreSQL connection string
            schema: Database schema to use (typically 'demo')
            output_dir: Directory to save the Excel file
            scale: Data volume - 'small', 'medium', 'large'
            problem_ratio: Percentage of problematic patterns (0.0-1.0)
            app_concentration: How many apps per database - 'low', 'medium', 'high'
            seed: Random seed for reproducible generation (None for random)
            pending_ratio: Percentage of components with pending discovery (0.0-1.0)
                          0.0 = all complete (default), 1.0 = all pending
        """
        self.connection_string = connection_string
        self.schema = schema
        self.output_dir = output_dir
        self.scale = scale
        self.problem_ratio = problem_ratio
        self.app_concentration = app_concentration
        self.pending_ratio = pending_ratio
        
        # Set random seed for reproducibility
        if seed is not None:
            random.seed(seed)
            self.seed = seed
        else:
            # Use current timestamp as seed for randomness
            self.seed = int(datetime.now().timestamp())
            random.seed(self.seed)
            
        self.workbook = None
        self.formats = {}
        self.conn = None
        
        # Component tracking
        self.components = []
        self.relationships = []
        self.component_map = {}  # Map component_id to component for easy lookup
        
        # Scale-based counts
        self.scale_configs = {
            'small': {
                'total_components': 50,
                'app_ratio': 0.60,
                'db_ratio': 0.12,
                'cache_ratio': 0.08,
                'mq_ratio': 0.05,
                'storage_ratio': 0.08,
                'lb_ratio': 0.04,
                'other_ratio': 0.03
            },
            'medium': {
                'total_components': 200,
                'app_ratio': 0.60,
                'db_ratio': 0.12,
                'cache_ratio': 0.08,
                'mq_ratio': 0.05,
                'storage_ratio': 0.08,
                'lb_ratio': 0.04,
                'other_ratio': 0.03
            },
            'large': {
                'total_components': 500,
                'app_ratio': 0.60,
                'db_ratio': 0.12,
                'cache_ratio': 0.08,
                'mq_ratio': 0.05,
                'storage_ratio': 0.08,
                'lb_ratio': 0.04,
                'other_ratio': 0.03
            }
        }
        
        # App concentration configs
        self.concentration_configs = {
            'low': {'min': 3, 'max': 5},
            'medium': {'min': 8, 'max': 12},
            'high': {'min': 15, 'max': 20}
        }
        
        # Reference data (loaded from database)
        self.component_types = {}
        self.component_subtypes = {}
        self.environments = {}
        self.statuses = {}
        self.abstraction_levels = {}
        self.physical_locations = {}
        self.relationship_types = {}
        self.protocols = {}  # Add protocols lookup
        self.subtype_parent_map = {}
        
        # Counters
        self.component_id_counter = 1
        self.relationship_id_counter = 1
        self.mac_counter = 1
        
        # Track problems created
        self.problems_created = []
        self.good_patterns_created = []
        
    def connect_to_database(self):
        """Establish connection to PostgreSQL database."""
        try:
            print(f"Connecting to database...")
            self.conn = psycopg2.connect(self.connection_string)
            print(f"Successfully connected to database")
            
            # Set schema
            with self.conn.cursor() as cur:
                cur.execute(f"SET search_path TO {self.schema}, public")
            
            return True
        except psycopg2.Error as e:
            print(f"ERROR: Failed to connect to database: {e}")
            return False
            
    def load_reference_data(self):
        """Load all reference data from the database."""
        print("Loading reference data from database...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Load component types
            cur.execute(f"SELECT component_type_id, type_name FROM {self.schema}.component_types")
            for row in cur.fetchall():
                self.component_types[row['type_name']] = row['component_type_id']
            print(f"  Loaded {len(self.component_types)} component types")
            
            # Load component subtypes with parent type mapping
            cur.execute(f"""
                SELECT s.component_subtype_id, s.subtype_name, s.component_type_id, t.type_name
                FROM {self.schema}.component_subtypes s
                JOIN {self.schema}.component_types t ON s.component_type_id = t.component_type_id
            """)
            for row in cur.fetchall():
                self.component_subtypes[row['subtype_name']] = row['component_subtype_id']
                self.subtype_parent_map[row['component_subtype_id']] = row['type_name']
            print(f"  Loaded {len(self.component_subtypes)} component subtypes")
            
            # Load environments
            cur.execute(f"SELECT environment_id, environment_name FROM {self.schema}.component_environments")
            for row in cur.fetchall():
                self.environments[row['environment_name']] = row['environment_id']
            print(f"  Loaded {len(self.environments)} environments")
            
            # Load operational statuses
            cur.execute(f"SELECT ops_status_id, status_name FROM {self.schema}.component_ops_statuses")
            for row in cur.fetchall():
                self.statuses[row['status_name']] = row['ops_status_id']
            print(f"  Loaded {len(self.statuses)} operational statuses")
            
            # Load abstraction levels
            cur.execute(f"SELECT abstraction_level_id, level_name FROM {self.schema}.component_abstraction_levels")
            for row in cur.fetchall():
                self.abstraction_levels[row['level_name']] = row['abstraction_level_id']
            print(f"  Loaded {len(self.abstraction_levels)} abstraction levels")
            
            # Load physical locations
            cur.execute(f"SELECT physical_location_id, location_name FROM {self.schema}.component_physical_locations")
            for row in cur.fetchall():
                self.physical_locations[row['location_name']] = row['physical_location_id']
            print(f"  Loaded {len(self.physical_locations)} physical locations")
            
            # Load relationship types
            cur.execute(f"SELECT relationship_type_id, type_name FROM {self.schema}.component_relationship_types")
            for row in cur.fetchall():
                self.relationship_types[row['type_name']] = row['relationship_type_id']
            print(f"  Loaded {len(self.relationship_types)} relationship types")

            # Load protocols
            cur.execute(f"SELECT protocol_id, protocol_name FROM {self.schema}.component_protocols")
            for row in cur.fetchall():
                self.protocols[row['protocol_name']] = row['protocol_id']
            print(f"  Loaded {len(self.protocols)} protocols")
            
    def get_next_mac(self) -> str:
        """Generate next MAC address in sequence."""
        mac = f"00:1B:44:11:3A:{self.mac_counter:02X}"
        self.mac_counter += 1
        return mac
        
    def get_ip_for_location_and_type(self, location_name: str, component_fqdn: str) -> str:
        """Generate IP address based on location and component type."""
        # Extract datacenter number from location name
        dc_num = '1'  # default
        if 'DC01' in location_name or 'AL' in location_name:
            dc_num = '1'
        elif 'DC02' in location_name or 'NC' in location_name:
            dc_num = '2'
        elif 'DC03' in location_name or 'VA' in location_name:
            dc_num = '3'
            
        base = f"10.{dc_num}"
        
        # Assign subnets by component type
        if any(x in component_fqdn for x in ['app', 'web', 'portal', 'mobile', 'api']):
            subnet = random.randint(10, 20)
        elif any(x in component_fqdn for x in ['db', 'database']):
            subnet = random.randint(30, 40)
        elif any(x in component_fqdn for x in ['redis', 'cache']):
            subnet = random.randint(35, 45)
        elif any(x in component_fqdn for x in ['kafka', 'mq']):
            subnet = random.randint(50, 60)
        elif any(x in component_fqdn for x in ['nas', 'san', 'minio', 'obj']):
            subnet = random.randint(70, 80)
        elif 'lb' in component_fqdn:
            subnet = random.randint(5, 9)
        else:
            subnet = random.randint(90, 99)
            
        host = random.randint(10, 250)
        return f"{base}.{subnet}.{host}"
        
            
    def get_vlan_for_type(self, component_fqdn: str) -> int:
        """Assign VLAN based on component type."""
        if any(x in component_fqdn for x in ['app', 'web', 'portal', 'mobile', 'api']):
            return random.randint(100, 199)
        elif any(x in component_fqdn for x in ['db', 'redis', 'cache']):
            return random.randint(200, 299)
        elif any(x in component_fqdn for x in ['nas', 'san', 'minio', 'obj']):
            return random.randint(300, 399)
        elif 'lb' in component_fqdn:
            return random.randint(10, 20)
        else:
            return random.randint(100, 199)
            
    def get_port_for_type(self, component_fqdn: str) -> int:
        """Assign port based on component type."""
        if 'redis' in component_fqdn or 'cache' in component_fqdn:
            return 6379
        elif 'kafka' in component_fqdn or 'mq' in component_fqdn:
            return 9092
        elif 'db' in component_fqdn:
            return 5432
        elif 'nas' in component_fqdn or 'nfs' in component_fqdn:
            return 2049
        elif 'san' in component_fqdn:
            return 3260
        elif 'minio' in component_fqdn or 'obj' in component_fqdn:
            return 9000
        elif 'lb' in component_fqdn:
            return 443
        else:
            return 443  # Default HTTPS
            
    def determine_subtype(self, fqdn: str, component_type_name: str) -> Optional[int]:
        """Determine the appropriate subtype ID based on FQDN and component type."""
        # Find subtypes that belong to this component type
        valid_subtypes = []
        for subtype_name, subtype_id in self.component_subtypes.items():
            if self.subtype_parent_map.get(subtype_id) == component_type_name:
                valid_subtypes.append((subtype_name, subtype_id))
        
        if not valid_subtypes:
            return None
            
        # Match based on FQDN patterns
        fqdn_lower = fqdn.lower()
        
        # For applications
        if component_type_name == 'application':
            if 'api' in fqdn_lower or 'service' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'api' in name.lower():
                        return id
            elif 'batch' in fqdn_lower or 'job' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'batch' in name.lower():
                        return id
            # Default to web_application
            for name, id in valid_subtypes:
                if 'web' in name.lower():
                    return id
                    
        # For polyglot_persistence
        elif component_type_name == 'polyglot_persistence':
            if 'redis' in fqdn_lower or 'cache' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'cache' in name.lower():
                        return id
            elif 'kafka' in fqdn_lower or 'mq' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'message' in name.lower() or 'queue' in name.lower():
                        return id
            elif 'db' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'relational' in name.lower():
                        return id
                        
        # For block_level_persistence
        elif component_type_name == 'block_level_persistence':
            if 'nas' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'network_attached' in name.lower() or 'nas' in name.lower():
                        return id
            elif 'san' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'storage_area' in name.lower() or 'san' in name.lower():
                        return id
            elif 'minio' in fqdn_lower or 'obj' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'object' in name.lower():
                        return id
                        
        # For networking
        elif component_type_name == 'networking':
            if 'lb' in fqdn_lower or 'load' in fqdn_lower:
                for name, id in valid_subtypes:
                    if 'load' in name.lower():
                        return id
                        
        # Return first valid subtype as fallback
        return valid_subtypes[0][1] if valid_subtypes else None
        
    def get_short_name(self, fqdn: str) -> str:
        """Extract short name from FQDN for readable descriptions."""
        # webapp01.prod.dc01.regions.com -> webapp01.dc01
        parts = fqdn.split('.')
        if len(parts) >= 4:
            return f"{parts[0]}.{parts[2]}"
        return parts[0] if parts else fqdn
        
    def create_component(self, fqdn: str, location_name: str, component_type_name: str,
                        description: str, status_name: str = 'OPERATIONAL',
                        abstraction_name: str = 'virtual_machine') -> Dict:
        """
        Create a component record using reference data from database.

        This method intentionally overrides schema defaults for complete records
        to provide meaningful, realistic data. For pending discovery records,
        it allows the database to use its defaults (auto-generated FQDNs, _PT_PENDING_ values).
        """

        # Validate inputs
        if location_name not in self.physical_locations:
            return None

        if component_type_name not in self.component_types:
            return None

        if status_name not in self.statuses:
            status_name = 'OPERATIONAL'

        if abstraction_name not in self.abstraction_levels:
            abstraction_name = 'virtual_machine'

        # Decide if this component is in pending discovery state
        is_pending = random.random() < self.pending_ratio

        if is_pending:
            # PENDING DISCOVERY: Simulate incomplete data collection
            # Some fields use database defaults, others use _PT_PENDING_

            # Determine quality grade based on how much is missing
            missing_level = random.choice(['partial', 'minimal'])
            if missing_level == 'minimal':
                # Very little data collected
                record_quality = '_PT_RED_RECORD_'
                # Don't provide FQDN - let database generate pthost-XXX.example.regions.com
                fqdn_value = None  # Will be excluded from INSERT to use DB default
                app_code = '_PT_PENDING_'
                desc = '_PT_PENDING_'
                # Basic network info might still be pending
                ip = '0.0.0.0'
                mac = '00:00:00:00:00:00'
                vlan = 1
                port = 1
            else:
                # Partial data collected
                record_quality = '_PT_YELLOW_RECORD_'
                # Might have FQDN or not
                fqdn_value = fqdn if random.random() > 0.5 else None
                app_code = f'APP{self.component_id_counter:03d}' if random.random() > 0.5 else '_PT_PENDING_'
                desc = description if random.random() > 0.5 else '_PT_PENDING_'
                # Network info partially discovered
                ip = self.get_ip_for_location_and_type(location_name, fqdn) if random.random() > 0.3 else '0.0.0.0'
                mac = self.get_next_mac() if random.random() > 0.3 else '00:00:00:00:00:00'
                vlan = self.get_vlan_for_type(fqdn) if random.random() > 0.3 else 1
                port = self.get_port_for_type(fqdn) if random.random() > 0.3 else 1
        else:
            # COMPLETE RECORD: Override all defaults with meaningful values
            record_quality = '_PT_GREEN_RECORD_'
            fqdn_value = fqdn
            app_code = f'APP{self.component_id_counter:03d}'
            desc = description
            ip = self.get_ip_for_location_and_type(location_name, fqdn)
            mac = self.get_next_mac()
            vlan = self.get_vlan_for_type(fqdn)
            port = self.get_port_for_type(fqdn)

        # Determine subtype (even for pending, we try to guess based on partial info)
        subtype_id = self.determine_subtype(fqdn if fqdn_value else 'unknown', component_type_name)
        if not subtype_id:
            subtype_id = 999  # _PT_PENDING_ subtype

        component = {
            'component_id': self.component_id_counter,
            'physical_location_id': self.physical_locations[location_name],
            'vlan': vlan,
            'ip': ip,
            'port': port,
            'mac': mac,
            'app_code': app_code,
            'protocol_id': self.protocols.get('HTTPS', 999),  # Use 999 (_PT_PENDING_) for unknown
            'record_quality_grade': record_quality,
            'component_type_id': self.component_types[component_type_name],
            'component_subtype_id': subtype_id,
            'description': desc,
            'environment_id': self.environments.get('PROD', 999),
            'abstraction_level_id': self.abstraction_levels.get(abstraction_name, 999),
            'ops_status_id': self.statuses.get(status_name, 999),
            'created_at': datetime.now(),
            'created_by': 'demo_data_generator_v2',
            'updated_at': datetime.now(),
            'updated_by': 'demo_data_generator_v2'
        }

        # Only include FQDN if we have a value (otherwise use DB default)
        if fqdn_value:
            component['fqdn'] = fqdn_value

        self.components.append(component)
        self.component_map[self.component_id_counter] = component
        self.component_id_counter += 1
        return component
        
    def create_relationship(self, component_id: int, related_id: int,
                          rel_type_name: str, description: str) -> Dict:
        """Create a relationship record with human-readable description."""
        
        if rel_type_name not in self.relationship_types:
            return None
            
        # Get component names for readable description
        comp1 = self.component_map.get(component_id)
        comp2 = self.component_map.get(related_id)

        if not comp1 or not comp2:
            return None

        # Create human-readable description - handle missing FQDNs
        comp1_name = self.get_short_name(comp1.get('fqdn', f'component_{comp1["component_id"]}'))
        comp2_name = self.get_short_name(comp2.get('fqdn', f'component_{comp2["component_id"]}'))
        full_description = f"{comp1_name} =[{rel_type_name}]=> {comp2_name}: {description}"
        
        relationship = {
            'relationship_id': self.relationship_id_counter,
            'component_id': component_id,
            'related_component_id': related_id,
            'relationship_type_id': self.relationship_types[rel_type_name],
            'description': full_description,
            'created_at': datetime.now(),
            'created_by': 'demo_data_generator',
            'updated_at': datetime.now(),
            'updated_by': 'demo_data_generator'
        }
        
        self.relationships.append(relationship)
        self.relationship_id_counter += 1
        return relationship
        
    def generate_components(self):
        """Generate components based on scale and ratios."""
        print(f"\nGenerating {self.scale} scale components...")
        
        config = self.scale_configs[self.scale]
        total = config['total_components']
        
        # Calculate component counts
        app_count = int(total * config['app_ratio'])
        db_count = int(total * config['db_ratio'])
        cache_count = int(total * config['cache_ratio'])
        mq_count = int(total * config['mq_ratio'])
        storage_count = int(total * config['storage_ratio'])
        lb_count = int(total * config['lb_ratio'])
        
        print(f"  Target counts: {app_count} apps, {db_count} DBs, {cache_count} caches, "
              f"{mq_count} MQs, {storage_count} storage, {lb_count} LBs")
        
        # Get available locations
        locations = list(self.physical_locations.keys())
        if not locations:
            print("ERROR: No physical locations found in database")
            return
            
        # Generate applications (majority)
        print(f"  Generating {app_count} applications...")
        for i in range(1, app_count + 1):
            location = random.choice(locations)
            
            # Vary application types
            app_type = random.choice(['webapp', 'portal', 'mobile', 'api', 'service', 'internal', 'batch'])
            fqdn = f"{app_type}{i:02d}.prod.{self.get_dc_code(location)}.regions.com"
            
            # Determine status (most operational, some degraded)
            status = 'OPERATIONAL' if random.random() > 0.15 else 'DEGRADED'
            
            descriptions = [
                "Customer-facing banking application",
                "Internal operations portal",
                "Mobile banking backend service",
                "API gateway for third-party integrations",
                "Batch processing job scheduler",
                "Microservice for account management",
                "Web portal for loan applications",
                "ATM network communication service"
            ]
            
            self.create_component(
                fqdn, location, 'application',
                random.choice(descriptions), status
            )
            
        # Generate databases
        print(f"  Generating {db_count} databases...")
        for i in range(1, db_count + 1):
            location = random.choice(locations)
            
            # Create primary/secondary pairs
            db_type = 'pri' if i % 2 == 1 else 'sec'
            fqdn = f"db{i:02d}{db_type}.prod.{self.get_dc_code(location)}.regions.com"
            
            self.create_component(
                fqdn, location, 'polyglot_persistence',
                f"{'Primary' if db_type == 'pri' else 'Secondary'} database for critical data"
            )
            
        # Generate caches
        print(f"  Generating {cache_count} caches...")
        for i in range(1, cache_count + 1):
            location = random.choice(locations)
            cache_type = random.choice(['redis', 'cache'])
            fqdn = f"{cache_type}{i:02d}.prod.{self.get_dc_code(location)}.regions.com"
            
            self.create_component(
                fqdn, location, 'polyglot_persistence',
                "High-performance cache for session/API data"
            )
            
        # Generate message queues
        print(f"  Generating {mq_count} message queues...")
        for i in range(1, mq_count + 1):
            location = random.choice(locations)
            mq_type = random.choice(['kafka', 'mq'])
            fqdn = f"{mq_type}{i:02d}.prod.{self.get_dc_code(location)}.regions.com"
            
            self.create_component(
                fqdn, location, 'polyglot_persistence',
                "Message broker for event streaming"
            )
            
        # Generate storage
        print(f"  Generating {storage_count} storage systems...")
        for i in range(1, storage_count + 1):
            location = random.choice(locations)
            storage_type = random.choice(['nas', 'san', 'minio', 'obj'])
            fqdn = f"{storage_type}{i:02d}.prod.{self.get_dc_code(location)}.regions.com"
            
            self.create_component(
                fqdn, location, 'block_level_persistence',
                "Enterprise storage for documents and backups"
            )
            
        # Generate load balancers
        print(f"  Generating {lb_count} load balancers...")
        for i in range(1, lb_count + 1):
            location = random.choice(locations)
            fqdn = f"lb{i:02d}.prod.{self.get_dc_code(location)}.regions.com"
            
            self.create_component(
                fqdn, location, 'networking',
                "Load balancer for application traffic distribution"
            )
            
        print(f"  Total components created: {len(self.components)}")
        
    def get_dc_code(self, location_name: str) -> str:
        """Extract datacenter code from location name."""
        if 'DC01' in location_name or 'AL' in location_name:
            return 'dc01'
        elif 'DC02' in location_name or 'NC' in location_name:
            return 'dc02'
        elif 'DC03' in location_name or 'VA' in location_name:
            return 'dc03'
        return 'dc01'
        
    def generate_relationships(self):
        """Generate relationships with intentional problems and good patterns."""
        print(f"\nGenerating relationships (problem ratio: {self.problem_ratio})...")

        # Group components by type - handle missing FQDNs
        apps = []
        dbs = []
        caches = []
        mqs = []
        storages = []
        lbs = []

        for c in self.components:
            # Use FQDN if present, otherwise use component_id as fallback for identification
            fqdn = c.get('fqdn', f'pending_{c["component_id"]}')

            if 'app' in fqdn or 'portal' in fqdn or 'mobile' in fqdn or 'api' in fqdn or 'service' in fqdn:
                apps.append(c)
            elif 'db' in fqdn:
                dbs.append(c)
            elif 'redis' in fqdn or 'cache' in fqdn:
                caches.append(c)
            elif 'kafka' in fqdn or 'mq' in fqdn:
                mqs.append(c)
            elif any(x in fqdn for x in ['nas', 'san', 'minio', 'obj']):
                storages.append(c)
            elif 'lb' in fqdn:
                lbs.append(c)
        
        # Create hub database (many apps depend on it)
        if dbs and apps:
            self.create_hub_database_pattern(apps, dbs)
            
        # Create failover patterns (good and bad)
        if len(dbs) >= 2:
            self.create_failover_patterns(dbs)
            
        # Create cache patterns (co-located and cross-DC)
        if apps and caches:
            self.create_cache_patterns(apps, caches)
            
        # Create message queue patterns
        if apps and mqs:
            self.create_mq_patterns(apps, mqs)
            
        # Create load balancer relationships
        if apps and lbs:
            self.create_lb_patterns(apps, lbs)
            
        # Create some circular dependencies
        if len(apps) >= 3 and random.random() < self.problem_ratio:
            self.create_circular_dependency(apps)
            
        # Create orphaned components (no relationships)
        self.create_orphaned_components()
        
        print(f"  Total relationships created: {len(self.relationships)}")
        print(f"  Problems created: {len(self.problems_created)}")
        print(f"  Good patterns created: {len(self.good_patterns_created)}")
        
    def create_hub_database_pattern(self, apps: List[Dict], dbs: List[Dict]):
        """Create a hub database that many applications depend on."""
        # Pick first primary database as hub
        hub_db = next((d for d in dbs if 'pri' in d.get('fqdn', '')), dbs[0])
        
        # Determine how many apps should connect based on concentration
        concentration = self.concentration_configs[self.app_concentration]
        num_apps = random.randint(concentration['min'], concentration['max'])
        num_apps = min(num_apps, len(apps))  # Don't exceed available apps
        
        print(f"  Creating hub database pattern: {num_apps} apps -> {self.get_short_name(hub_db.get('fqdn', f'component_{hub_db['component_id']}'))}")
        
        # Connect apps to hub database
        selected_apps = random.sample(apps, num_apps)
        for app in selected_apps:
            self.create_relationship(
                app['component_id'],
                hub_db['component_id'],
                'persists_to',
                f"HUB PATTERN: One of {num_apps} apps using central database"
            )
            
        self.problems_created.append(f"Hub database with {num_apps} dependent applications")
        
    def create_failover_patterns(self, dbs: List[Dict]):
        """Create both good and bad failover configurations."""
        # Group databases by number (db01pri/db01sec, db02pri/db02sec, etc.)
        db_pairs = {}
        for db in dbs:
            # Extract number from fqdn (db01pri -> 01)
            import re
            fqdn = db.get('fqdn', '')
            if fqdn:
                match = re.search(r'db(\d+)', fqdn)
                if match:
                    db_num = match.group(1)
                    if db_num not in db_pairs:
                        db_pairs[db_num] = []
                    db_pairs[db_num].append(db)
                
        for db_num, pair in db_pairs.items():
            if len(pair) >= 2:
                primary = next((d for d in pair if 'pri' in d.get('fqdn', '')), None)
                secondary = next((d for d in pair if 'sec' in d.get('fqdn', '')), None)
                
                if primary and secondary:
                    # Check if they're in the same location
                    same_location = primary['physical_location_id'] == secondary['physical_location_id']
                    
                    if same_location:
                        # BAD pattern
                        self.create_relationship(
                            primary['component_id'],
                            secondary['component_id'],
                            'fails_over_to',
                            "ISSUE: Same-DC failover - no real disaster recovery!"
                        )
                        self.problems_created.append(f"Same-DC failover: {self.get_short_name(primary.get('fqdn', f'component_{primary['component_id']}'))}")
                    else:
                        # GOOD pattern
                        self.create_relationship(
                            primary['component_id'],
                            secondary['component_id'],
                            'fails_over_to',
                            "GOOD: Cross-DC failover for proper disaster recovery"
                        )
                        self.good_patterns_created.append(f"Cross-DC failover: {self.get_short_name(primary.get('fqdn', f'component_{primary['component_id']}'))}")
                        
    def create_cache_patterns(self, apps: List[Dict], caches: List[Dict]):
        """Create cache relationships with good co-location and bad cross-DC patterns."""
        # Each cache serves some apps
        for cache in caches:
            num_apps = random.randint(2, 5)
            selected_apps = random.sample(apps, min(num_apps, len(apps)))
            
            for app in selected_apps:
                # Check if co-located
                same_location = app['physical_location_id'] == cache['physical_location_id']
                
                if same_location:
                    # GOOD: Co-located
                    self.create_relationship(
                        app['component_id'],
                        cache['component_id'],
                        'persists_to',
                        "GOOD: Co-located cache for low latency"
                    )
                    self.good_patterns_created.append(f"Co-located cache: {self.get_short_name(app.get('fqdn', f'component_{app['component_id']}'))}")
                else:
                    # Determine if this should be a problem
                    if random.random() < self.problem_ratio:
                        # BAD: Cross-DC cache
                        self.create_relationship(
                            app['component_id'],
                            cache['component_id'],
                            'persists_to',
                            "ISSUE: Cross-datacenter cache access adding latency"
                        )
                        self.problems_created.append(f"Cross-DC cache: {self.get_short_name(app.get('fqdn', f'component_{app['component_id']}'))}")
                    else:
                        # Acceptable: Some cross-DC is normal
                        self.create_relationship(
                            app['component_id'],
                            cache['component_id'],
                            'persists_to',
                            "Cross-DC cache access (acceptable for this use case)"
                        )
                        
    def create_mq_patterns(self, apps: List[Dict], mqs: List[Dict]):
        """Create message queue patterns with publishers and subscribers."""
        for mq in mqs:
            # Some apps publish
            num_publishers = random.randint(1, 3)
            publishers = random.sample(apps, min(num_publishers, len(apps)))
            
            for pub in publishers:
                self.create_relationship(
                    pub['component_id'],
                    mq['component_id'],
                    'publishes_to',
                    "Publishing events to message queue"
                )
                
            # Some apps subscribe
            num_subscribers = random.randint(2, 5)
            subscribers = random.sample(apps, min(num_subscribers, len(apps)))
            
            for sub in subscribers:
                self.create_relationship(
                    sub['component_id'],
                    mq['component_id'],
                    'subscribes_to',
                    "Subscribing to events from message queue"
                )
                
        # Create replication pattern for Kafka
        kafka_nodes = [m for m in mqs if 'kafka' in m.get('fqdn', '')]
        if len(kafka_nodes) >= 2:
            # Check if all in same location (BAD)
            locations = set(k['physical_location_id'] for k in kafka_nodes)
            if len(locations) == 1:
                # All in same DC - BAD
                primary = kafka_nodes[0]
                for replica in kafka_nodes[1:]:
                    self.create_relationship(
                        replica['component_id'],
                        primary['component_id'],
                        'replicates_from',
                        "ISSUE: All Kafka replicas in same datacenter!"
                    )
                self.problems_created.append("Kafka cluster with no geographic distribution")
            else:
                # Distributed - GOOD
                primary = kafka_nodes[0]
                for replica in kafka_nodes[1:]:
                    self.create_relationship(
                        replica['component_id'],
                        primary['component_id'],
                        'replicates_from',
                        "GOOD: Geographic distribution for Kafka cluster"
                    )
                self.good_patterns_created.append("Properly distributed Kafka cluster")
                
    def create_lb_patterns(self, apps: List[Dict], lbs: List[Dict]):
        """Create load balancer relationships."""
        for lb in lbs:
            # Each LB serves multiple apps
            num_apps = random.randint(3, 8)
            selected_apps = random.sample(apps, min(num_apps, len(apps)))
            
            for app in selected_apps:
                # Prefer same location but not required
                same_location = app['physical_location_id'] == lb['physical_location_id']
                
                if same_location:
                    self.create_relationship(
                        app['component_id'],
                        lb['component_id'],
                        'proxied_by',
                        "Load balanced for high availability"
                    )
                else:
                    self.create_relationship(
                        app['component_id'],
                        lb['component_id'],
                        'proxied_by',
                        "Cross-DC load balancing (higher latency)"
                    )
                    
    def create_circular_dependency(self, apps: List[Dict]):
        """Create a circular dependency pattern (problematic)."""
        # Pick 3 random apps
        circular_apps = random.sample(apps, 3)
        
        # Create circle: app1 -> app2 -> app3 -> app1
        self.create_relationship(
            circular_apps[0]['component_id'],
            circular_apps[1]['component_id'],
            'consumes_api_from',
            "ISSUE: Part of circular dependency chain"
        )
        
        self.create_relationship(
            circular_apps[1]['component_id'],
            circular_apps[2]['component_id'],
            'consumes_api_from',
            "ISSUE: Part of circular dependency chain"
        )
        
        self.create_relationship(
            circular_apps[2]['component_id'],
            circular_apps[0]['component_id'],
            'consumes_api_from',
            "ISSUE: Circular dependency - potential deadlock!"
        )
        
        self.problems_created.append(f"Circular dependency between {self.get_short_name(circular_apps[0].get('fqdn', f'component_{circular_apps[0]['component_id']}'))}, "
                                    f"{self.get_short_name(circular_apps[1].get('fqdn', f'component_{circular_apps[1]['component_id']}'))}, "
                                    f"{self.get_short_name(circular_apps[2].get('fqdn', f'component_{circular_apps[2]['component_id']}'))}")
                                    
    def create_orphaned_components(self):
        """Mark some components as orphaned (no relationships)."""
        # Count components with no relationships
        components_with_rels = set()
        for rel in self.relationships:
            components_with_rels.add(rel['component_id'])
            components_with_rels.add(rel['related_component_id'])
            
        orphaned = []
        for comp in self.components:
            if comp['component_id'] not in components_with_rels:
                orphaned.append(comp)
                # Update description to indicate orphaned status
                comp['description'] = f"ORPHANED: {comp['description']} - No active connections!"
                
        if orphaned:
            print(f"  Created {len(orphaned)} orphaned components (resource waste)")
            self.problems_created.append(f"{len(orphaned)} orphaned components wasting resources")
            
    def create_workbook_formats(self):
        """Create reusable formats for the workbook with color coding."""
        self.formats['header'] = self.workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'text_wrap': True,
            'valign': 'vcenter'
        })
        
        self.formats['date'] = self.workbook.add_format({
            'num_format': 'yyyy-mm-dd hh:mm:ss',
            'border': 1
        })
        
        self.formats['cell'] = self.workbook.add_format({
            'border': 1,
            'valign': 'vcenter'
        })
        
        # Problem patterns (RED)
        self.formats['bad'] = self.workbook.add_format({
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006',
            'border': 1
        })
        
        # Good patterns (GREEN)
        self.formats['good'] = self.workbook.add_format({
            'bg_color': '#C6EFCE',
            'font_color': '#006100',
            'border': 1
        })
        
        # Warnings (YELLOW)
        self.formats['warning'] = self.workbook.add_format({
            'bg_color': '#FFEB9C',
            'font_color': '#9C5700',
            'border': 1
        })
        
        # Orphaned/Waste (GRAY)
        self.formats['orphaned'] = self.workbook.add_format({
            'bg_color': '#E0E0E0',
            'font_color': '#606060',
            'border': 1
        })
        
    def write_summary_sheet(self):
        """Write a summary sheet with statistics and configuration."""
        print("Writing Summary sheet...")
        
        worksheet = self.workbook.add_worksheet('Summary')
        
        row = 0
        
        # Title
        title_format = self.workbook.add_format({
            'bold': True,
            'font_size': 16,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        worksheet.merge_range(row, 0, row, 3, 'BAIS Demo Data - Network Segmentation Analysis', title_format)
        row += 2
        
        # Generation parameters
        section_format = self.workbook.add_format({'bold': True, 'bg_color': '#E0E0E0'})
        
        worksheet.write(row, 0, 'Generation Parameters', section_format)
        row += 1
        worksheet.write(row, 0, 'Generated:', self.formats['header'])
        worksheet.write(row, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        row += 1
        worksheet.write(row, 0, 'Schema:', self.formats['header'])
        worksheet.write(row, 1, self.schema)
        row += 1
        worksheet.write(row, 0, 'Scale:', self.formats['header'])
        worksheet.write(row, 1, self.scale)
        row += 1
        worksheet.write(row, 0, 'Problem Ratio:', self.formats['header'])
        worksheet.write(row, 1, f"{self.problem_ratio * 100:.0f}%")
        row += 1
        worksheet.write(row, 0, 'App Concentration:', self.formats['header'])
        worksheet.write(row, 1, self.app_concentration)
        row += 1
        worksheet.write(row, 0, 'Pending Ratio:', self.formats['header'])
        worksheet.write(row, 1, f"{self.pending_ratio * 100:.0f}%")
        row += 1
        worksheet.write(row, 0, 'Random Seed:', self.formats['header'])
        worksheet.write(row, 1, self.seed)
        row += 2
        
        # Component statistics
        worksheet.write(row, 0, 'Component Statistics', section_format)
        row += 1
        worksheet.write(row, 0, 'Total Components:', self.formats['header'])
        worksheet.write(row, 1, len(self.components))
        row += 1
        worksheet.write(row, 0, 'Total Relationships:', self.formats['header'])
        worksheet.write(row, 1, len(self.relationships))
        row += 2

        # Data quality statistics
        quality_counts = {'_PT_GREEN_RECORD_': 0, '_PT_YELLOW_RECORD_': 0, '_PT_RED_RECORD_': 0}
        for comp in self.components:
            grade = comp.get('record_quality_grade', '_PT_YELLOW_RECORD_')
            if grade in quality_counts:
                quality_counts[grade] += 1

        worksheet.write(row, 0, 'Data Quality Statistics', section_format)
        row += 1
        worksheet.write(row, 0, 'Complete (GREEN):', self.formats['header'])
        worksheet.write(row, 1, f"{quality_counts['_PT_GREEN_RECORD_']} components", self.formats['good'])
        row += 1
        worksheet.write(row, 0, 'Partial (YELLOW):', self.formats['header'])
        worksheet.write(row, 1, f"{quality_counts['_PT_YELLOW_RECORD_']} components", self.formats['warning'])
        row += 1
        worksheet.write(row, 0, 'Minimal (RED):', self.formats['header'])
        worksheet.write(row, 1, f"{quality_counts['_PT_RED_RECORD_']} components", self.formats['bad'])
        row += 2
        
        # Problems identified
        worksheet.write(row, 0, 'Problems Identified', section_format)
        row += 1
        for problem in self.problems_created[:10]:  # Show first 10
            worksheet.write(row, 1, f"• {problem}", self.formats['bad'])
            row += 1
        if len(self.problems_created) > 10:
            worksheet.write(row, 1, f"... and {len(self.problems_created) - 10} more", self.formats['bad'])
            row += 1
        row += 1
        
        # Good patterns
        worksheet.write(row, 0, 'Good Patterns', section_format)
        row += 1
        for pattern in self.good_patterns_created[:5]:  # Show first 5
            worksheet.write(row, 1, f"• {pattern}", self.formats['good'])
            row += 1
        if len(self.good_patterns_created) > 5:
            worksheet.write(row, 1, f"... and {len(self.good_patterns_created) - 5} more", self.formats['good'])
            row += 1
            
        # Auto-adjust column widths
        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 1, 50)
        
        print("  Summary written")
        
    def write_components_sheet(self):
        """Write the biz_components sheet with color-coded descriptions."""
        print("Writing biz_components sheet...")
        
        worksheet = self.workbook.add_worksheet('biz_components')
        
        # Get actual column names from database
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = 'biz_components'
                ORDER BY ordinal_position
            """, (self.schema,))
            headers = [row[0] for row in cur.fetchall()]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, self.formats['header'])
        
        # Write component data
        for row_idx, comp in enumerate(self.components, start=1):
            for col, header in enumerate(headers):
                if header in comp:
                    value = comp[header]
                    
                    # Apply color coding based on description content
                    if header == 'description':
                        if 'ORPHANED' in value:
                            worksheet.write(row_idx, col, value, self.formats['orphaned'])
                        elif 'ISSUE' in value or 'PROBLEM' in value:
                            worksheet.write(row_idx, col, value, self.formats['bad'])
                        elif 'HUB' in value or 'central' in value.lower():
                            worksheet.write(row_idx, col, value, self.formats['warning'])
                        elif 'proper' in value.lower() or 'good' in value.lower():
                            worksheet.write(row_idx, col, value, self.formats['good'])
                        else:
                            worksheet.write(row_idx, col, value, self.formats['cell'])
                    elif isinstance(value, datetime):
                        worksheet.write_datetime(row_idx, col, value, self.formats['date'])
                    else:
                        worksheet.write(row_idx, col, value, self.formats['cell'])
        
        # Auto-adjust column widths
        worksheet.set_column(0, len(headers)-1, 15)
        if 'fqdn' in headers:
            worksheet.set_column(headers.index('fqdn'), headers.index('fqdn'), 35)
        if 'description' in headers:
            worksheet.set_column(headers.index('description'), headers.index('description'), 50)
        
        # Freeze header row
        worksheet.freeze_panes(1, 0)
        
        print(f"  Wrote {len(self.components)} components")
        
    def write_relationships_sheet(self):
        """Write the biz_component_relationships sheet with color-coded descriptions."""
        print("Writing biz_component_relationships sheet...")
        
        worksheet = self.workbook.add_worksheet('biz_component_relationships')
        
        # Get actual column names from database
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = 'biz_component_relationships'
                ORDER BY ordinal_position
            """, (self.schema,))
            headers = [row[0] for row in cur.fetchall()]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, self.formats['header'])
        
        # Write relationship data
        for row_idx, rel in enumerate(self.relationships, start=1):
            for col, header in enumerate(headers):
                if header in rel:
                    value = rel[header]
                    
                    # Apply color coding based on description content
                    if header == 'description':
                        if 'ISSUE' in value or 'PROBLEM' in value:
                            worksheet.write(row_idx, col, value, self.formats['bad'])
                        elif 'GOOD' in value:
                            worksheet.write(row_idx, col, value, self.formats['good'])
                        elif 'WARNING' in value or 'HUB' in value:
                            worksheet.write(row_idx, col, value, self.formats['warning'])
                        else:
                            worksheet.write(row_idx, col, value, self.formats['cell'])
                    elif isinstance(value, datetime):
                        worksheet.write_datetime(row_idx, col, value, self.formats['date'])
                    else:
                        worksheet.write(row_idx, col, value, self.formats['cell'])
        
        # Auto-adjust column widths
        worksheet.set_column(0, len(headers)-1, 18)
        if 'description' in headers:
            worksheet.set_column(headers.index('description'), headers.index('description'), 80)
        
        # Freeze header row
        worksheet.freeze_panes(1, 0)
        
        print(f"  Wrote {len(self.relationships)} relationships")
        
    def write_reference_tables_sheet(self):
        """Write reference data sheet."""
        print("Writing Reference_Tables sheet...")
        
        worksheet = self.workbook.add_worksheet('Reference_Tables')
        
        reference_tables = [
            'component_types',
            'component_subtypes', 
            'component_environments',
            'component_ops_statuses',
            'component_abstraction_levels',
            'component_physical_locations',
            'component_relationship_types'
        ]
        
        row = 0
        
        for table in reference_tables:
            # Check if table exists
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    )
                """, (self.schema, table))
                exists = cur.fetchone()[0]
                
            if not exists:
                continue
                
            # Write table name
            worksheet.write(row, 0, table, self.formats['header'])
            row += 1
            
            # Get and write data
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM {self.schema}.{table} ORDER BY 1")
                data = cur.fetchall()
                
                if data:
                    # Write column headers
                    columns = list(data[0].keys())
                    for col_idx, col_name in enumerate(columns):
                        worksheet.write(row, col_idx, col_name, self.formats['header'])
                    row += 1
                    
                    # Write data
                    for data_row in data:
                        for col_idx, col_name in enumerate(columns):
                            value = data_row.get(col_name)
                            if isinstance(value, datetime):
                                worksheet.write_datetime(row, col_idx, value, self.formats['date'])
                            elif value is not None:
                                worksheet.write(row, col_idx, value)
                        row += 1
                        
            row += 1  # Blank row between tables
            
        # Auto-adjust column widths
        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 5, 30)
        
        print("  Reference tables written")
        
    def generate_excel(self) -> bool:
        """Main method to generate the Excel file."""
        
        # Connect to database
        if not self.connect_to_database():
            return False
            
        try:
            # Load reference data
            self.load_reference_data()
            
            # Generate components and relationships
            self.generate_components()
            self.generate_relationships()
            
            # Create Excel file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"editable_seed_spreadsheet_{timestamp}.xlsx"
            filepath = os.path.join(self.output_dir, filename)
            
            print(f"\nCreating Excel file: {filename}")
            self.workbook = xlsxwriter.Workbook(filepath)
            self.create_workbook_formats()
            
            # Write sheets
            self.write_summary_sheet()
            self.write_components_sheet()
            self.write_relationships_sheet()
            self.write_reference_tables_sheet()
            
            # Close workbook
            self.workbook.close()
            
            print(f"\n{'='*60}")
            print(f"Excel file successfully created: {filepath}")
            print(f"{'='*60}")
            print(f"Summary:")
            print(f"  - Components: {len(self.components)}")
            print(f"  - Relationships: {len(self.relationships)}")
            print(f"  - Problems identified: {len(self.problems_created)}")
            print(f"  - Good patterns: {len(self.good_patterns_created)}")
            print(f"\nColor coding in spreadsheet:")
            print(f"  🔴 Red = Critical problems")
            print(f"  🟢 Green = Good patterns")
            print(f"  🟡 Yellow = Warnings")
            print(f"  ⚫ Gray = Orphaned/waste")
            print(f"\nReady for import to database or graph visualization!")
            
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to generate Excel: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if self.conn:
                self.conn.close()


def show_verbose_help():
    """Display detailed help information for all options."""
    help_text = """
================================================================================
BAIS Demo Data Generator - Detailed Help (v3)
================================================================================

This tool generates realistic enterprise infrastructure demo data with
intentional architectural problems for consulting demonstrations.

OPTIONS WITH DETAILED EXPLANATIONS:
====================================

--scale {small,medium,large}
-----------------------------
Controls the total number of components generated.

  Component distributions (approximate):
  - 60% Applications (web apps, APIs, microservices)
  - 12% Databases (primary/secondary pairs)
  - 8% Caches (Redis, in-memory stores)
  - 5% Message queues (Kafka, MQ)
  - 8% Storage systems (NAS, SAN, object storage)
  - 4% Load balancers
  - 3% Other networking components

  Counts by scale:
  • small:   50 total components  (~30 apps, 6 DBs, 4 caches)
  • medium:  200 total components (~120 apps, 24 DBs, 16 caches)
  • large:   500 total components (~300 apps, 60 DBs, 40 caches)

  Examples:
  --scale small    # Quick demos, fast processing
  --scale medium   # Typical enterprise subset (default)
  --scale large    # Full enterprise simulation

--problem-ratio RATIO
----------------------
Controls architectural problems in generated data (0.0 to 1.0, default: 0.3).

  Problems Created (Bad Patterns):
  • Hub database anti-pattern: 8-20 apps depending on single database
  • Same-DC failover: Primary/secondary DBs in same location (no real DR)
  • Cross-DC cache access: Apps using caches in different datacenters
  • Circular dependencies: Apps depending on each other in loops
  • Orphaned components: Infrastructure with no connections (waste)
  • Single-DC Kafka: All message queue replicas in same datacenter

  Good Patterns (for comparison):
  • Cross-DC failover: Proper disaster recovery setup
  • Co-located caches: Low latency cache access
  • Distributed Kafka: Geographic redundancy

  Examples:
  --problem-ratio 0.0   # Perfect architecture (unrealistic)
  --problem-ratio 0.3   # Typical enterprise issues (default)
  --problem-ratio 0.7   # Problematic architecture needing help
  --problem-ratio 1.0   # Maximum chaos for dramatic demos

--pending-ratio RATIO
---------------------
Controls data discovery completeness (0.0 to 1.0, default: 0.0).

  Simulates incomplete infrastructure discovery:
  • 0.0 = All data complete (traditional demo)
  • 0.2 = 20% components partially discovered
  • 0.5 = Half components missing data
  • 1.0 = All components pending discovery

  Data Quality Grades:
  • GREEN (_PT_GREEN_RECORD_): Complete data, meaningful FQDNs
  • YELLOW (_PT_YELLOW_RECORD_): Partial data, some fields pending
  • RED (_PT_RED_RECORD_): Minimal data, auto-generated FQDNs

  Pending components will have:
  • Auto-generated FQDNs: pthost-001.example.regions.com
  • _PT_PENDING_ placeholders in various fields
  • Basic network info as 0.0.0.0 or 00:00:00:00:00:00

  Use cases:
  --pending-ratio 0.0   # Full discovery complete (default)
  --pending-ratio 0.2   # Realistic partial discovery
  --pending-ratio 0.5   # Mid-discovery phase demo
  --pending-ratio 1.0   # Just started discovery

--app-concentration {low,medium,high}
--------------------------------------
Controls how many applications depend on each database.

  Demonstrates database bottleneck patterns:
  • low:    3-5 apps per database (good separation)
  • medium: 8-12 apps per database (typical enterprise)
  • high:   15-20 apps per database (bottleneck problem)

  This creates the "hub database" anti-pattern where too many
  applications depend on a single database, causing:
  - Performance bottlenecks
  - Difficult maintenance windows
  - Cascading failures
  - Scaling challenges

  Examples:
  --app-concentration low     # Well-architected
  --app-concentration medium  # Typical issues (default)
  --app-concentration high    # Severe bottleneck

--seed NUMBER
-------------
Random seed for reproducible data generation.

  Use cases:
  • Testing: Generate identical data for regression tests
  • Demos: Ensure consistent data across presentations
  • Debugging: Reproduce specific data patterns

  Examples:
  --seed 42        # Deterministic generation
  --seed 12345     # Different but reproducible dataset
  (no --seed)      # Random data each time

--randomize
-----------
Force random generation even with default settings.

  By default, the tool uses seed=42 for reproducibility.
  Use --randomize to force truly random generation.

OUTPUT:
=======
Generates an Excel file with color-coded data:
  🔴 Red    = Critical problems requiring attention
  🟢 Green  = Good architectural patterns
  🟡 Yellow = Warning conditions
  ⚫ Gray   = Orphaned/wasted resources

Sheets included:
  • Summary: Configuration and statistics
  • biz_components: All infrastructure components
  • biz_component_relationships: Dependencies and connections
  • Reference_Tables: Lookup data for types, statuses, etc.

EXAMPLES:
=========
  # Typical enterprise with common problems
  python generate_demo_data_excel.py --scale medium --problem-ratio 0.3

  # Demonstrate discovery in progress
  python generate_demo_data_excel.py --scale small --pending-ratio 0.4

  # Show severe bottleneck issues
  python generate_demo_data_excel.py --scale large --problem-ratio 0.7 \\
                                      --app-concentration high

  # Reproducible test data
  python generate_demo_data_excel.py --seed 42 --scale small

================================================================================
For basic help, use --help
"""
    print(help_text)
    sys.exit(0)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate demo data Excel for BAIS infrastructure consulting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate typical enterprise data
  python %(prog)s --scale medium --problem-ratio 0.3

  # Show detailed help for all options
  python %(prog)s --verbose-help

  # Generate with pending discovery simulation
  python %(prog)s --scale small --pending-ratio 0.2
        """,
        add_help=False  # We'll add custom help
    )

    # Help arguments
    parser.add_argument(
        '-h', '--help',
        action='help',
        help='Show basic help message and exit'
    )

    parser.add_argument(
        '--verbose-help',
        action='store_true',
        help='Show detailed explanations for all options'
    )

    parser.add_argument(
        '--schema',
        default='demo',
        help='Database schema to use for reference data (default: demo)'
    )

    parser.add_argument(
        '--scale',
        choices=['small', 'medium', 'large'],
        default='medium',
        help='Component count: small=50, medium=200, large=500 (default: medium)'
    )

    parser.add_argument(
        '--problem-ratio',
        type=float,
        default=0.3,
        help='Architectural problems ratio 0.0-1.0 (default: 0.3=typical enterprise)'
    )

    parser.add_argument(
        '--app-concentration',
        choices=['low', 'medium', 'high'],
        default='medium',
        help='Apps per database: low=3-5, medium=8-12, high=15-20 (default: medium)'
    )

    parser.add_argument(
        '--pending-ratio',
        type=float,
        default=0.0,
        help='Incomplete discovery ratio 0.0-1.0 (default: 0.0=all complete)'
    )

    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for reproducible data (default: 42)'
    )

    parser.add_argument(
        '--randomize',
        action='store_true',
        help='Force random generation (overrides default seed=42)'
    )
    
    args = parser.parse_args()

    # Check for verbose help first
    if args.verbose_help:
        show_verbose_help()

    # Validate problem ratio
    if not 0.0 <= args.problem_ratio <= 1.0:
        print("ERROR: problem-ratio must be between 0.0 and 1.0")
        sys.exit(1)

    # Validate pending ratio
    if not 0.0 <= args.pending_ratio <= 1.0:
        print("ERROR: pending-ratio must be between 0.0 and 1.0")
        sys.exit(1)
        
    # Handle seed logic
    if args.randomize:
        seed = None
    elif args.seed is not None:
        seed = args.seed
    else:
        # Default to deterministic with seed 42
        seed = 42
        
    # Find project root
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    
    # Find project root by searching for .env file
    current = script_dir.resolve()
    project_root = None
    while current != current.parent:
        env_file = current / '.env'
        if env_file.exists():
            project_root = current
            break
        current = current.parent
    
    if not project_root:
        print("ERROR: Could not find project root (.env file not found)")
        sys.exit(1)
    
    # Load environment variables
    env_file = project_root / '.env'
    load_dotenv(env_file, override=True)
    
    # Get database connection string
    connection_string = os.environ.get('POSTGRESQL_BAIS_DB_ADMIN_URL')
    if not connection_string:
        print("ERROR: POSTGRESQL_BAIS_DB_ADMIN_URL not found in environment variables")
        sys.exit(1)
    
    # Display connection information
    from urllib.parse import urlparse
    parsed = urlparse(connection_string)
    print(f"{'='*60}")
    print("DATABASE CONNECTION INFO")
    print(f"{'='*60}")
    print(f"  Host:     {parsed.hostname}")
    print(f"  Port:     {parsed.port}")
    print(f"  Database: {parsed.path.lstrip('/')}")
    print(f"  User:     {parsed.username}")
    print(f"  Password: {'*' * 8 if parsed.password else 'not set'}")
    print(f"  Schema:   {args.schema}")
    print(f"{'='*60}")
    print()
    
    # Output directory - now in the same directory as the scripts
    output_dir = script_dir / '..' / 'spreadsheets.d/'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"{'='*60}")
    print(f"BAIS Demo Data Generator - Network Segmentation Consulting Tool")
    print(f"{'='*60}")
    print(f"Configuration:")
    print(f"  Project root: {project_root}")
    print(f"  Output directory: {output_dir}")
    print(f"  Schema: {args.schema}")
    print(f"  Scale: {args.scale}")
    print(f"  Problem ratio: {args.problem_ratio * 100:.0f}%")
    print(f"  App concentration: {args.app_concentration}")
    print(f"  Pending ratio: {args.pending_ratio * 100:.0f}%")
    print(f"  Seed: {seed if seed is not None else 'random'}")
    
    # Create generator and run
    generator = DemoDataGenerator(
        connection_string,
        args.schema,
        str(output_dir),
        scale=args.scale,
        problem_ratio=args.problem_ratio,
        app_concentration=args.app_concentration,
        seed=seed,
        pending_ratio=args.pending_ratio
    )
    
    success = generator.generate_excel()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
