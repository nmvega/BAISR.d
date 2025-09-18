#!/usr/bin/env python3
"""
Demo Data Spreadsheet Generator for BAIS Database (Version 2)

This script generates an Excel spreadsheet with realistic demo data for business demonstrations.
It connects to the PostgreSQL database to fetch reference data and creates a spreadsheet with
three tabs: biz_components, biz_component_relationships, and ref_tables.

Version 2 improvements:
- Uses hidden sheet with ranges for dropdowns to bypass Excel's 255 char limit
- Bold borders and professional formatting
- Consolas font throughout
- Light green background for data cells
- More relationships (40-50)
- Proper column ordering for readability
- Dereferenced FKs in ref_tables
"""

import os
import sys
import psycopg2
import xlsxwriter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import random
import ipaddress
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / '.env')


class DemoDataGeneratorV2:
    """Generates demo data spreadsheet with realistic business data - Version 2."""

    def __init__(self):
        """Initialize the generator with database connection."""
        self.conn = None
        self.reference_data = {}
        self.demo_components = []
        self.demo_relationships = []
        self.workbook = None
        self.formats = {}

    def connect_to_database(self):
        """Connect to PostgreSQL database using environment variables."""
        try:
            # Get database URL from environment
            db_url = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_URL')
            if not db_url:
                raise ValueError("POSTGRESQL_BAIS_DB_ADMIN_URL not found in environment variables")

            # Parse the URL and connect
            self.conn = psycopg2.connect(db_url)
            print("✓ Connected to database")
            return True

        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False

    def fetch_reference_data(self, schema='live'):
        """Fetch all reference table data from the database."""
        cursor = self.conn.cursor()

        # Define reference tables and their key columns
        ref_tables = {
            'component_types': ('component_type_id', 'type_name', 'description'),
            'component_subtypes': ('component_subtype_id', 'subtype_name', 'description', 'component_type_id'),
            'component_environments': ('environment_id', 'environment_name', 'description'),
            'component_ops_statuses': ('ops_status_id', 'status_name', 'description'),
            'component_physical_locations': ('physical_location_id', 'location_name', 'description'),
            'component_relationship_types': ('relationship_type_id', 'type_name', 'description'),
            'component_abstraction_levels': ('abstraction_level_id', 'level_name', 'description'),
            'component_protocols': ('protocol_id', 'protocol_name', 'description')
        }

        for table, columns in ref_tables.items():
            query = f"SELECT {', '.join(columns)} FROM {schema}.{table} ORDER BY {columns[0]}"
            cursor.execute(query)

            # Store with column names
            self.reference_data[table] = {
                'columns': columns,
                'data': cursor.fetchall()
            }
            print(f"  • Fetched {len(self.reference_data[table]['data'])} rows from {table}")

        cursor.close()
        print("✓ Reference data fetched")

    def create_formats(self, workbook):
        """Create all the formats we'll use in the spreadsheet."""
        self.workbook = workbook

        # Header format - dark blue background, white text, bold borders
        self.formats['header'] = workbook.add_format({
            'bold': True,
            'bg_color': '#1F4E78',
            'font_color': 'white',
            'font_name': 'Consolas',
            'font_size': 11,
            'border': 2,  # Bold border
            'border_color': '#1F4E78',
            'align': 'center',
            'valign': 'vcenter'
        })

        # Data cell format - light green background, bold borders
        self.formats['cell'] = workbook.add_format({
            'bg_color': '#D7E4BC',
            'font_name': 'Consolas',
            'font_size': 10,
            'border': 2,  # Bold border
            'border_color': '#1F4E78',
            'align': 'left',
            'valign': 'vcenter'
        })

        # Number cell format - same as cell but right-aligned
        self.formats['number_cell'] = workbook.add_format({
            'bg_color': '#D7E4BC',
            'font_name': 'Consolas',
            'font_size': 10,
            'border': 2,
            'border_color': '#1F4E78',
            'align': 'right',
            'valign': 'vcenter'
        })

        # Blank separator format
        self.formats['separator'] = workbook.add_format({
            'bg_color': 'white',
            'font_name': 'Consolas'
        })

    def generate_demo_components(self):
        """Generate 50 rows of demo component data."""
        components = []
        component_id = 1

        # Helper to get random MAC address
        def random_mac():
            return ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)])

        # Rows 1-5: Minimal/default entries
        for i in range(1, 6):
            components.append({
                'component_id': component_id,
                'fqdn': f'pthost-{i:03d}.example.regions.com',
                'app_code': '_PT_PENDING_',
                'physical_location_id': '999: _PT_PENDING_',
                'vlan': 1,
                'ip': '0.0.0.0',
                'port': 1,
                'mac': '00:00:00:00:00:00',
                'protocol_id': '999: _PT_PENDING_',
                'component_type_id': '999: _PT_PENDING_',
                'component_subtype_id': '999: [_PT_PENDING_] _PT_PENDING_',
                'description': '_PT_PENDING_',
                'environment_id': '999: _PT_PENDING_',
                'abstraction_level_id': '999: _PT_PENDING_',
                'ops_status_id': '999: _PT_PENDING_',
                'record_quality_grade': '_PT_YELLOW_RECORD_',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': 'demo_generator',
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_by': 'demo_generator'
            })
            component_id += 1

        # Rows 6-15: Production Web Applications
        web_apps = [
            ('web-app-prod', 'DC01_AL', 'Main customer portal'),
            ('api-gateway', 'DC02_NC', 'API gateway for microservices'),
            ('customer-portal', 'DC03_VA', 'Customer self-service portal'),
            ('admin-console', 'DC01_AL', 'Administrative interface'),
            ('mobile-backend', 'DC02_NC', 'Mobile app backend services'),
            ('payment-service', 'DC03_VA', 'Payment processing service'),
            ('auth-service', 'DC01_AL', 'Authentication service'),
            ('notification-api', 'DC02_NC', 'Email/SMS notification service'),
            ('reporting-app', 'DC03_VA', 'Business reporting application'),
            ('analytics-dashboard', 'DC01_AL', 'Real-time analytics dashboard')
        ]

        for i, (name, location, desc) in enumerate(web_apps):
            dc = location.split('_')[0].lower()
            location_id = {'DC01_AL': 1, 'DC02_NC': 2, 'DC03_VA': 3}[location]
            vlan = 100 + (i % 3) * 10  # VLANs 100, 110, 120

            components.append({
                'component_id': component_id,
                'fqdn': f'{name}.{dc}.example.regions.com',
                'app_code': f'APP{component_id:03d}',
                'physical_location_id': f'{location_id}: {location}',
                'vlan': vlan,
                'ip': f'10.{location_id}.{vlan}.{10 + i}',
                'port': 443 if 'api' in name or 'service' in name else 8080,
                'mac': random_mac(),
                'protocol_id': '2: HTTPS',
                'component_type_id': '1: application',
                'component_subtype_id': '2: [application] api_service' if 'api' in name or 'service' in name else '1: [application] web_application',
                'description': desc,
                'environment_id': '4: PROD',
                'abstraction_level_id': '3: container',
                'ops_status_id': '1: OPERATIONAL',
                'record_quality_grade': '_PT_GREEN_RECORD_',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': 'demo_generator',
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_by': 'demo_generator'
            })
            component_id += 1

        # Rows 16-25: Databases
        databases = [
            ('postgres-master', 'DC01_AL', 5432, 'Primary PostgreSQL database', '5: [polyglot_persistence] relational_database'),
            ('postgres-replica', 'DC01_AL', 5432, 'PostgreSQL read replica', '5: [polyglot_persistence] relational_database'),
            ('mysql-prod', 'DC02_NC', 3306, 'MySQL database for legacy app', '5: [polyglot_persistence] relational_database'),
            ('mongodb-cluster', 'DC03_VA', 27017, 'MongoDB document store', '6: [polyglot_persistence] nosql_database'),
            ('redis-cache-01', 'DC01_AL', 6379, 'Redis cache layer', '8: [polyglot_persistence] cache'),
            ('redis-cache-02', 'DC02_NC', 6379, 'Redis cache layer', '8: [polyglot_persistence] cache'),
            ('elasticsearch', 'DC03_VA', 9200, 'Elasticsearch for search', '6: [polyglot_persistence] nosql_database'),
            ('kafka-broker-01', 'DC01_AL', 9092, 'Kafka message broker', '7: [polyglot_persistence] message_queue'),
            ('kafka-broker-02', 'DC02_NC', 9092, 'Kafka message broker', '7: [polyglot_persistence] message_queue'),
            ('rabbitmq', 'DC03_VA', 5672, 'RabbitMQ message queue', '7: [polyglot_persistence] message_queue')
        ]

        for name, location, port, desc, subtype in databases:
            dc = location.split('_')[0].lower()
            location_id = {'DC01_AL': 1, 'DC02_NC': 2, 'DC03_VA': 3}[location]
            vlan = 200  # Database VLAN

            components.append({
                'component_id': component_id,
                'fqdn': f'{name}.{dc}.example.regions.com',
                'app_code': f'DB{component_id:03d}',
                'physical_location_id': f'{location_id}: {location}',
                'vlan': vlan,
                'ip': f'10.{location_id}.{vlan}.{component_id}',
                'port': port,
                'mac': random_mac(),
                'protocol_id': '3: TCP',
                'component_type_id': '2: polyglot_persistence',
                'component_subtype_id': subtype,
                'description': desc,
                'environment_id': '4: PROD',
                'abstraction_level_id': '2: virtual_machine',
                'ops_status_id': '1: OPERATIONAL',
                'record_quality_grade': '_PT_GREEN_RECORD_',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': 'demo_generator',
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_by': 'demo_generator'
            })
            component_id += 1

        # Rows 26-35: Networking Components
        network_components = [
            ('lb-prod-01', 'DC01_AL', 80, 'Production load balancer', '12: [networking] load_balancer'),
            ('lb-prod-02', 'DC02_NC', 443, 'Production load balancer', '12: [networking] load_balancer'),
            ('firewall-main', 'DC01_AL', 22, 'Main firewall', '14: [networking] firewall'),
            ('firewall-dmz', 'DC02_NC', 22, 'DMZ firewall', '14: [networking] firewall'),
            ('api-gateway-lb', 'DC03_VA', 443, 'API Gateway load balancer', '13: [networking] api_gateway'),
            ('switch-core-01', 'DC01_AL', 161, 'Core network switch', '15: [networking] switch'),
            ('switch-core-02', 'DC02_NC', 161, 'Core network switch', '15: [networking] switch'),
            ('vpn-gateway', 'DC03_VA', 1194, 'VPN gateway', '14: [networking] firewall'),
            ('cdn-edge', 'DC01_AL', 443, 'CDN edge server', '12: [networking] load_balancer'),
            ('dns-resolver', 'DC02_NC', 53, 'Internal DNS resolver', '15: [networking] switch')
        ]

        for name, location, port, desc, subtype in network_components:
            dc = location.split('_')[0].lower()
            location_id = {'DC01_AL': 1, 'DC02_NC': 2, 'DC03_VA': 3}[location]
            vlan = 10  # Management VLAN for network devices

            components.append({
                'component_id': component_id,
                'fqdn': f'{name}.{dc}.example.regions.com',
                'app_code': f'NET{component_id:03d}',
                'physical_location_id': f'{location_id}: {location}',
                'vlan': vlan,
                'ip': f'10.{location_id}.{vlan}.{component_id}',
                'port': port,
                'mac': random_mac(),
                'protocol_id': '3: TCP' if port != 53 else '4: UDP',
                'component_type_id': '4: networking',
                'component_subtype_id': subtype,
                'description': desc,
                'environment_id': '4: PROD',
                'abstraction_level_id': '1: physical_bare_metal' if 'switch' in name else '2: virtual_machine',
                'ops_status_id': '1: OPERATIONAL',
                'record_quality_grade': '_PT_GREEN_RECORD_',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': 'demo_generator',
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_by': 'demo_generator'
            })
            component_id += 1

        # Rows 36-50: Development/Test Systems
        dev_systems = [
            ('app-dev-01', 'DC01_AL', 'DEV', 'Development application server'),
            ('app-dev-02', 'DC01_AL', 'DEV', 'Development application server'),
            ('db-dev', 'DC01_AL', 'DEV', 'Development database'),
            ('test-api', 'DC02_NC', 'TEST', 'Test API server'),
            ('test-web', 'DC02_NC', 'TEST', 'Test web server'),
            ('test-db', 'DC02_NC', 'TEST', 'Test database'),
            ('staging-web', 'DC03_VA', 'STAGING', 'Staging web server'),
            ('staging-api', 'DC03_VA', 'STAGING', 'Staging API server'),
            ('staging-db', 'DC03_VA', 'STAGING', 'Staging database'),
            ('qa-automation', 'DC01_AL', 'QA', 'QA automation server'),
            ('qa-testing', 'DC02_NC', 'QA', 'QA testing server'),
            ('uat-app', 'DC03_VA', 'UAT', 'UAT application server'),
            ('uat-db', 'DC03_VA', 'UAT', 'UAT database'),
            ('dr-backup', 'DC02_NC', 'DR', 'Disaster recovery backup'),
            ('jenkins-ci', 'DC01_AL', 'DEV', 'CI/CD server')
        ]

        env_map = {
            'DEV': '1: DEV',
            'TEST': '2: TEST',
            'STAGING': '3: STAGING',
            'QA': '6: QA',
            'UAT': '5: UAT',
            'DR': '7: DR'
        }

        for name, location, env, desc in dev_systems:
            dc = location.split('_')[0].lower()
            location_id = {'DC01_AL': 1, 'DC02_NC': 2, 'DC03_VA': 3}[location]
            vlan = 300 if env == 'DEV' else 310 if env == 'TEST' else 320

            is_db = 'db' in name or 'database' in desc.lower()

            components.append({
                'component_id': component_id,
                'fqdn': f'{name}.{dc}.example.regions.com',
                'app_code': f'{env[:3]}{component_id:03d}',
                'physical_location_id': f'{location_id}: {location}',
                'vlan': vlan,
                'ip': f'10.{location_id}.{vlan}.{component_id}',
                'port': 5432 if is_db else 8080,
                'mac': random_mac(),
                'protocol_id': '3: TCP' if is_db else '1: HTTP',
                'component_type_id': '2: polyglot_persistence' if is_db else '1: application',
                'component_subtype_id': '5: [polyglot_persistence] relational_database' if is_db else '1: [application] web_application',
                'description': desc,
                'environment_id': env_map[env],
                'abstraction_level_id': '2: virtual_machine' if is_db else '3: container',
                'ops_status_id': '1: OPERATIONAL' if env != 'DR' else '6: PLANNED',
                'record_quality_grade': '_PT_GREEN_RECORD_',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': 'demo_generator',
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_by': 'demo_generator'
            })
            component_id += 1

        self.demo_components = components[:50]  # Limit to 50 rows
        print(f"✓ Generated {len(self.demo_components)} demo components")

    def generate_demo_relationships(self):
        """Generate 40-50 relationships between components."""
        relationships = []
        rel_id = 1

        # Helper to find component by partial name
        def find_component(partial_name):
            for comp in self.demo_components:
                if partial_name in comp['fqdn']:
                    return comp
            return None

        # Web apps persist to databases (expanded)
        web_db_pairs = [
            ('web-app-prod', 'postgres-master'),
            ('customer-portal', 'postgres-master'),
            ('admin-console', 'mysql-prod'),
            ('mobile-backend', 'mongodb-cluster'),
            ('payment-service', 'postgres-master'),
            ('auth-service', 'redis-cache-01'),
            ('analytics-dashboard', 'elasticsearch'),
            ('reporting-app', 'postgres-master'),
            ('notification-api', 'postgres-master'),
            ('api-gateway', 'redis-cache-02'),
            ('app-dev-01', 'db-dev'),
            ('app-dev-02', 'db-dev'),
            ('test-api', 'test-db'),
            ('test-web', 'test-db'),
            ('staging-api', 'staging-db'),
            ('staging-web', 'staging-db'),
            ('uat-app', 'uat-db'),
        ]

        for web, db in web_db_pairs:
            web_comp = find_component(web)
            db_comp = find_component(db)
            if web_comp and db_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{web_comp['component_id']}: {web_comp['fqdn']}",
                    'relationship_type_id': '4: persists_to',
                    'related_component_id': f"{db_comp['component_id']}: {db_comp['fqdn']}",
                    'description': f'{web} persists data to {db}',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        # Database replication relationships
        replication_pairs = [
            ('postgres-replica', 'postgres-master'),
            ('redis-cache-02', 'redis-cache-01'),
            ('kafka-broker-02', 'kafka-broker-01'),
        ]

        for replica, master in replication_pairs:
            replica_comp = find_component(replica)
            master_comp = find_component(master)
            if replica_comp and master_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{replica_comp['component_id']}: {replica_comp['fqdn']}",
                    'relationship_type_id': '1: replicates_from',
                    'related_component_id': f"{master_comp['component_id']}: {master_comp['fqdn']}",
                    'description': f'{replica} replicates from {master}',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        # Load balancer relationships (expanded)
        lb_app_pairs = [
            ('lb-prod-01', 'web-app-prod'),
            ('lb-prod-01', 'customer-portal'),
            ('lb-prod-01', 'admin-console'),
            ('lb-prod-02', 'api-gateway'),
            ('lb-prod-02', 'mobile-backend'),
            ('api-gateway-lb', 'auth-service'),
            ('api-gateway-lb', 'payment-service'),
            ('api-gateway-lb', 'notification-api'),
            ('cdn-edge', 'web-app-prod'),
            ('cdn-edge', 'customer-portal'),
        ]

        for lb, app in lb_app_pairs:
            lb_comp = find_component(lb)
            app_comp = find_component(app)
            if lb_comp and app_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{app_comp['component_id']}: {app_comp['fqdn']}",
                    'relationship_type_id': '13: load_balanced_by',
                    'related_component_id': f"{lb_comp['component_id']}: {lb_comp['fqdn']}",
                    'description': f'{app} traffic distributed by {lb}',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        # API consumption relationships (expanded)
        api_consumer_pairs = [
            ('web-app-prod', 'api-gateway'),
            ('mobile-backend', 'api-gateway'),
            ('customer-portal', 'auth-service'),
            ('admin-console', 'reporting-app'),
            ('payment-service', 'notification-api'),
            ('analytics-dashboard', 'api-gateway'),
            ('web-app-prod', 'auth-service'),
            ('customer-portal', 'payment-service'),
            ('mobile-backend', 'notification-api'),
        ]

        for consumer, api in api_consumer_pairs:
            consumer_comp = find_component(consumer)
            api_comp = find_component(api)
            if consumer_comp and api_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{consumer_comp['component_id']}: {consumer_comp['fqdn']}",
                    'relationship_type_id': '3: consumes_api_from',
                    'related_component_id': f"{api_comp['component_id']}: {api_comp['fqdn']}",
                    'description': f'{consumer} consumes API from {api}',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        # Message queue relationships
        publishers = ['payment-service', 'auth-service', 'notification-api', 'analytics-dashboard']
        subscribers = ['notification-api', 'reporting-app', 'analytics-dashboard', 'admin-console']

        for publisher in publishers[:2]:
            pub_comp = find_component(publisher)
            kafka_comp = find_component('kafka-broker-01')
            if pub_comp and kafka_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{pub_comp['component_id']}: {pub_comp['fqdn']}",
                    'relationship_type_id': '5: publishes_to',
                    'related_component_id': f"{kafka_comp['component_id']}: {kafka_comp['fqdn']}",
                    'description': f'{publisher} publishes events to Kafka',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        for subscriber in subscribers[:2]:
            sub_comp = find_component(subscriber)
            kafka_comp = find_component('kafka-broker-01')
            if sub_comp and kafka_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{sub_comp['component_id']}: {sub_comp['fqdn']}",
                    'relationship_type_id': '6: subscribes_to',
                    'related_component_id': f"{kafka_comp['component_id']}: {kafka_comp['fqdn']}",
                    'description': f'{subscriber} subscribes to events',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        # Peering relationships
        peer_pairs = [
            ('kafka-broker-01', 'kafka-broker-02'),
            ('switch-core-01', 'switch-core-02'),
            ('app-dev-01', 'app-dev-02'),
        ]

        for peer1, peer2 in peer_pairs:
            peer1_comp = find_component(peer1)
            peer2_comp = find_component(peer2)
            if peer1_comp and peer2_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{peer1_comp['component_id']}: {peer1_comp['fqdn']}",
                    'relationship_type_id': '11: peers_with',
                    'related_component_id': f"{peer2_comp['component_id']}: {peer2_comp['fqdn']}",
                    'description': f'{peer1} peers with {peer2}',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        # Monitoring relationships
        monitoring_pairs = [
            ('analytics-dashboard', 'web-app-prod'),
            ('analytics-dashboard', 'api-gateway'),
            ('analytics-dashboard', 'postgres-master'),
        ]

        for monitor, target in monitoring_pairs:
            monitor_comp = find_component(monitor)
            target_comp = find_component(target)
            if monitor_comp and target_comp:
                relationships.append({
                    'relationship_id': rel_id,
                    'component_id': f"{monitor_comp['component_id']}: {monitor_comp['fqdn']}",
                    'relationship_type_id': '9: monitors',
                    'related_component_id': f"{target_comp['component_id']}: {target_comp['fqdn']}",
                    'description': f'{monitor} monitors {target}',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': 'demo_generator',
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_by': 'demo_generator'
                })
                rel_id += 1

        self.demo_relationships = relationships[:50]  # Limit to 50 relationships
        print(f"✓ Generated {len(self.demo_relationships)} demo relationships")

    def create_excel_file(self):
        """Create the Excel file with formatting and dropdowns."""
        # Create output directory if it doesn't exist
        output_dir = project_root / 'app' / 'scripts' / 'spreadsheets.d'
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = output_dir / f'business_showcase_data_spreadsheet_{timestamp}.xlsx'

        # Create workbook and formats
        workbook = xlsxwriter.Workbook(str(filename))
        self.create_formats(workbook)

        # Create hidden dropdown data sheet FIRST
        self._create_dropdown_data_sheet(workbook)

        # Create visible worksheets
        self._create_components_sheet(workbook)
        self._create_relationships_sheet(workbook)
        self._create_ref_tables_sheet(workbook)

        # Close workbook
        workbook.close()
        print(f"✓ Created Excel file: {filename.name}")
        return filename

    def _create_dropdown_data_sheet(self, workbook):
        """Create a hidden sheet with all dropdown data for range references."""
        worksheet = workbook.add_worksheet('dropdown_data')
        worksheet.hide()  # Hide this sheet from users

        col = 0
        self.dropdown_ranges = {}

        # Component types
        types_data = self._get_dropdown_list('component_types', 'component_type_id', 'type_name')
        worksheet.write(0, col, 'component_types')
        for row, value in enumerate(types_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['component_types'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(types_data)+1}'
        col += 1

        # Component subtypes with parent hints
        subtypes_data = self._get_subtype_dropdown_list()
        worksheet.write(0, col, 'component_subtypes')
        for row, value in enumerate(subtypes_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['component_subtypes'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(subtypes_data)+1}'
        col += 1

        # Environments
        env_data = self._get_dropdown_list('component_environments', 'environment_id', 'environment_name')
        worksheet.write(0, col, 'environments')
        for row, value in enumerate(env_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['environments'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(env_data)+1}'
        col += 1

        # Operational statuses
        status_data = self._get_dropdown_list('component_ops_statuses', 'ops_status_id', 'status_name')
        worksheet.write(0, col, 'ops_statuses')
        for row, value in enumerate(status_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['ops_statuses'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(status_data)+1}'
        col += 1

        # Physical locations
        location_data = self._get_dropdown_list('component_physical_locations', 'physical_location_id', 'location_name')
        worksheet.write(0, col, 'locations')
        for row, value in enumerate(location_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['locations'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(location_data)+1}'
        col += 1

        # Abstraction levels
        abstraction_data = self._get_dropdown_list('component_abstraction_levels', 'abstraction_level_id', 'level_name')
        worksheet.write(0, col, 'abstraction_levels')
        for row, value in enumerate(abstraction_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['abstraction_levels'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(abstraction_data)+1}'
        col += 1

        # Protocols
        protocol_data = self._get_dropdown_list('component_protocols', 'protocol_id', 'protocol_name')
        worksheet.write(0, col, 'protocols')
        for row, value in enumerate(protocol_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['protocols'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(protocol_data)+1}'
        col += 1

        # Record quality grades
        quality_data = ['_PT_GREEN_RECORD_', '_PT_YELLOW_RECORD_', '_PT_RED_RECORD_']
        worksheet.write(0, col, 'quality_grades')
        for row, value in enumerate(quality_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['quality_grades'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(quality_data)+1}'
        col += 1

        # Component list for relationships
        component_data = [f"{comp['component_id']}: {comp['fqdn']}" for comp in self.demo_components]
        worksheet.write(0, col, 'components')
        for row, value in enumerate(component_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['components'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(component_data)+1}'
        col += 1

        # Relationship types
        rel_type_data = self._get_dropdown_list('component_relationship_types', 'relationship_type_id', 'type_name')
        worksheet.write(0, col, 'relationship_types')
        for row, value in enumerate(rel_type_data, 1):
            worksheet.write(row, col, value)
        self.dropdown_ranges['relationship_types'] = f'dropdown_data!${chr(65+col)}$2:${chr(65+col)}${len(rel_type_data)+1}'

    def _create_components_sheet(self, workbook):
        """Create the biz_components worksheet with data and dropdowns."""
        worksheet = workbook.add_worksheet('biz_components')

        # Define columns
        columns = [
            'component_id', 'fqdn', 'app_code', 'physical_location_id', 'vlan', 'ip', 'port', 'mac',
            'protocol_id', 'component_type_id', 'component_subtype_id', 'description',
            'environment_id', 'abstraction_level_id', 'ops_status_id', 'record_quality_grade',
            'created_at', 'created_by', 'updated_at', 'updated_by'
        ]

        # Write headers
        for col, header in enumerate(columns):
            worksheet.write(0, col, header, self.formats['header'])

        # Write data rows
        for row_idx, component in enumerate(self.demo_components, start=1):
            for col_idx, col_name in enumerate(columns):
                value = component.get(col_name, '')
                # Use number format for numeric columns
                if col_name in ['component_id', 'vlan', 'port']:
                    worksheet.write(row_idx, col_idx, value, self.formats['number_cell'])
                else:
                    worksheet.write(row_idx, col_idx, value, self.formats['cell'])

        # Apply data validation using ranges
        max_row = len(self.demo_components)

        # All dropdown validations using ranges
        dropdown_configs = [
            ('component_type_id', 'component_types'),
            ('component_subtype_id', 'component_subtypes'),
            ('environment_id', 'environments'),
            ('ops_status_id', 'ops_statuses'),
            ('physical_location_id', 'locations'),
            ('abstraction_level_id', 'abstraction_levels'),
            ('protocol_id', 'protocols'),
            ('record_quality_grade', 'quality_grades')
        ]

        for column_name, range_key in dropdown_configs:
            if column_name in columns:
                col_idx = columns.index(column_name)
                worksheet.data_validation(
                    1, col_idx, max_row, col_idx,
                    {
                        'validate': 'list',
                        'source': self.dropdown_ranges[range_key]
                    }
                )

        # Auto-fit columns
        for col in range(len(columns)):
            worksheet.set_column(col, col, 22)

        # Freeze top row
        worksheet.freeze_panes(1, 0)

    def _create_relationships_sheet(self, workbook):
        """Create the biz_component_relationships worksheet with swapped column order."""
        worksheet = workbook.add_worksheet('biz_component_relationships')

        # Define columns - SWAPPED ORDER for relationship_type_id
        columns = [
            'relationship_id', 'component_id', 'relationship_type_id', 'related_component_id',
            'description', 'created_at', 'created_by', 'updated_at', 'updated_by'
        ]

        # Write headers
        for col, header in enumerate(columns):
            worksheet.write(0, col, header, self.formats['header'])

        # Write data rows (adjusting for swapped columns)
        for row_idx, relationship in enumerate(self.demo_relationships, start=1):
            for col_idx, col_name in enumerate(columns):
                value = relationship.get(col_name, '')
                if col_name == 'relationship_id':
                    worksheet.write(row_idx, col_idx, value, self.formats['number_cell'])
                else:
                    worksheet.write(row_idx, col_idx, value, self.formats['cell'])

        # Apply data validation using ranges
        max_row = len(self.demo_relationships)

        # Component dropdowns
        if 'component_id' in columns:
            col_idx = columns.index('component_id')
            worksheet.data_validation(
                1, col_idx, max_row, col_idx,
                {
                    'validate': 'list',
                    'source': self.dropdown_ranges['components']
                }
            )

        # Relationship type dropdown
        if 'relationship_type_id' in columns:
            col_idx = columns.index('relationship_type_id')
            worksheet.data_validation(
                1, col_idx, max_row, col_idx,
                {
                    'validate': 'list',
                    'source': self.dropdown_ranges['relationship_types']
                }
            )

        # Related component dropdown
        if 'related_component_id' in columns:
            col_idx = columns.index('related_component_id')
            worksheet.data_validation(
                1, col_idx, max_row, col_idx,
                {
                    'validate': 'list',
                    'source': self.dropdown_ranges['components']
                }
            )

        # Auto-fit columns
        for col in range(len(columns)):
            worksheet.set_column(col, col, 35)

        # Freeze top row
        worksheet.freeze_panes(1, 0)

    def _create_ref_tables_sheet(self, workbook):
        """Create the ref_tables worksheet with all reference data and dereferenced FKs."""
        worksheet = workbook.add_worksheet('ref_tables')

        current_row = 0

        # Build type lookup for dereferencing
        type_lookup = {}
        if 'component_types' in self.reference_data:
            type_data = self.reference_data['component_types']
            id_idx = type_data['columns'].index('component_type_id')
            name_idx = type_data['columns'].index('type_name')
            for row in type_data['data']:
                type_lookup[row[id_idx]] = f"{row[id_idx]}: {row[name_idx]}"

        # Write each reference table
        for table_name, table_data in self.reference_data.items():
            # Write table name header
            worksheet.write(current_row, 0, f'Table: {table_name}', self.formats['header'])
            worksheet.merge_range(current_row, 0, current_row, len(table_data['columns']) - 1,
                                 f'Table: {table_name}', self.formats['header'])
            current_row += 1

            # Write column headers
            for col_idx, col_name in enumerate(table_data['columns']):
                worksheet.write(current_row, col_idx, col_name, self.formats['header'])
            current_row += 1

            # Write data rows
            for row in table_data['data']:
                for col_idx, value in enumerate(row):
                    # Special handling for component_type_id in component_subtypes table
                    if table_name == 'component_subtypes' and table_data['columns'][col_idx] == 'component_type_id':
                        # Dereference the type ID to "id: name" format
                        if value in type_lookup:
                            value = type_lookup[value]

                    worksheet.write(current_row, col_idx, value, self.formats['cell'])
                current_row += 1

            # Add blank row separator (no formatting)
            current_row += 1

        # Auto-fit columns
        worksheet.set_column(0, 10, 30)

        # Freeze top row
        worksheet.freeze_panes(1, 0)

    def _get_dropdown_list(self, table_name, id_col, name_col):
        """Get dropdown list for a reference table in 'id: name' format."""
        dropdown_list = []

        if table_name in self.reference_data:
            columns = self.reference_data[table_name]['columns']
            id_idx = columns.index(id_col)
            name_idx = columns.index(name_col)

            for row in self.reference_data[table_name]['data']:
                dropdown_list.append(f"{row[id_idx]}: {row[name_idx]}")

        return dropdown_list

    def _get_subtype_dropdown_list(self):
        """Get subtype dropdown list with parent type hints."""
        dropdown_list = []

        if 'component_subtypes' in self.reference_data and 'component_types' in self.reference_data:
            # Get type names mapping
            type_names = {}
            type_columns = self.reference_data['component_types']['columns']
            type_id_idx = type_columns.index('component_type_id')
            type_name_idx = type_columns.index('type_name')

            for row in self.reference_data['component_types']['data']:
                type_names[row[type_id_idx]] = row[type_name_idx]

            # Build subtype list with parent hints
            subtype_columns = self.reference_data['component_subtypes']['columns']
            subtype_id_idx = subtype_columns.index('component_subtype_id')
            subtype_name_idx = subtype_columns.index('subtype_name')
            parent_type_idx = subtype_columns.index('component_type_id')

            for row in self.reference_data['component_subtypes']['data']:
                parent_type_name = type_names.get(row[parent_type_idx], 'unknown')
                dropdown_list.append(f"{row[subtype_id_idx]}: [{parent_type_name}] {row[subtype_name_idx]}")

        return dropdown_list

    def run(self):
        """Execute the complete demo data generation process."""
        print("\n=== BAIS Demo Data Spreadsheet Generator V2 ===\n")

        # Connect to database
        if not self.connect_to_database():
            return False

        # Fetch reference data
        self.fetch_reference_data()

        # Generate demo data
        self.generate_demo_components()
        self.generate_demo_relationships()

        # Create Excel file
        output_file = self.create_excel_file()

        # Close database connection
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")

        print(f"\n✅ Success! Demo data spreadsheet V2 created:\n   {output_file}")
        return True


def main():
    """Main entry point."""
    generator = DemoDataGeneratorV2()
    generator.run()


if __name__ == '__main__':
    main()
