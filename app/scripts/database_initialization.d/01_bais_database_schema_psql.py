#!/usr/bin/env python3
"""
BAIS Database Schema Script
===========================
Purpose: Setup complete BAIS database schema
Executes as: rc34924 (BAIS admin user)

This script creates:
- Service users (bais_ro, bais_rw)
- Shared functions
- All three schemas (live, live_masked, demo)
- All tables and permissions

Usage:
    # Run everything
    python bais_database_schema.py --no-dry-run
    
    # Run specific sections
    python bais_database_schema.py --section USER_CREATION --no-dry-run
    python bais_database_schema.py --section SCHEMA:live --no-dry-run
"""

import os
import sys
import subprocess
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"✓ Loaded environment from {env_file}")
else:
    print(f"⚠️  No .env file found at {env_file}, using system environment")

class BaisSchemaManager:
    """Manages BAIS database schema setup"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent.parent
        self.sql_file = self.script_dir.parent / 'database' / 'bais_database_schema.sql'
        self.sections = {}
        self._load_sections()
    
    def _load_sections(self):
        """Parse SQL file and extract sections"""
        if not self.sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {self.sql_file}")
        
        with open(self.sql_file, 'r') as f:
            content = f.read()
        
        # Pattern to match section markers
        section_pattern = r'-- ==================== SECTION: ([\w:]+) ====================\n(.*?)-- ==================== END SECTION: \1 ===================='
        
        matches = re.finditer(section_pattern, content, re.DOTALL)
        
        for match in matches:
            section_name = match.group(1)
            section_content = match.group(2)
            self.sections[section_name] = section_content
        
        print(f"📋 Loaded {len(self.sections)} sections from SQL file")
    
    def get_connection_url(self) -> str:
        """Get rc34924 connection URL from environment"""
        url = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_URL')
        if not url:
            # Build from components
            host = os.getenv('POSTGRESQL_INSTANCE_HOST', '0.0.0.0')
            port = os.getenv('POSTGRESQL_INSTANCE_PORT', '5432')
            user = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_USER', 'rc34924')
            password = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_PASSWORD', 'cBmVWgt8uzvyKj54x3E4Tn6s')
            database = os.getenv('POSTGRESQL_BAIS_DB', 'prutech_bais')
            url = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=disable"
        return url
    
    def list_sections(self):
        """List available sections"""
        print("\n📚 Available sections:")
        for name in self.sections:
            if name.startswith('SCHEMA:'):
                print(f"   • {name} (schema creation)")
            else:
                print(f"   • {name}")
    
    def execute_sql(self, sql_content: str, description: str, dry_run: bool = True) -> int:
        """Execute SQL content via psql"""
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Would execute: {description}")
            # Show first few lines of SQL
            lines = sql_content.strip().split('\n')
            preview = '\n'.join(lines[:10])
            if len(lines) > 10:
                preview += f"\n   ... ({len(lines) - 10} more lines)"
            print(f"   SQL Preview:\n{preview}")
            return 0
        
        print(f"\n🚀 Executing: {description}")
        
        url = self.get_connection_url()
        
        try:
            result = subprocess.run(
                ['psql', url, '-c', sql_content],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ ERROR executing SQL:")
                print(result.stderr)
                return 1
            
            # Count operations
            creates = result.stdout.count('CREATE')
            grants = result.stdout.count('GRANT')
            inserts = result.stdout.count('INSERT')
            
            print(f"   ✓ {creates} objects created")
            if grants > 0:
                print(f"   ✓ {grants} permissions granted")
            if inserts > 0:
                print(f"   ✓ {inserts} data rows inserted")
            
            return 0
            
        except FileNotFoundError:
            print("❌ ERROR: psql not found. Please install PostgreSQL client.")
            return 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return 1
    
    def run_section(self, section_name: str, dry_run: bool = True) -> int:
        """Run a specific section"""
        if section_name not in self.sections:
            print(f"❌ ERROR: Section '{section_name}' not found")
            self.list_sections()
            return 1
        
        sql_content = self.sections[section_name]
        
        # Add search path reset for schema sections
        if section_name.startswith('SCHEMA:'):
            sql_content = "SET search_path TO public;\n" + sql_content
        
        return self.execute_sql(sql_content, f"Section {section_name}", dry_run)
    
    def run_all(self, dry_run: bool = True) -> int:
        """Run all sections in order"""
        
        # Define execution order
        section_order = [
            'USER_CREATION',
            'DATABASE_PREREQUISITES',
            'SCHEMA:live',
            'SCHEMA:live_masked',
            'SCHEMA:demo',
            'PERMISSIONS'
        ]
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - Showing what would be executed:")
            print("   Sections to run in order:")
            for section in section_order:
                print(f"   • {section}")
            print("\n💡 To execute, run with --no-dry-run")
            return 0
        
        print(f"\n🚀 Running all {len(section_order)} sections...")
        
        for i, section in enumerate(section_order, 1):
            print(f"\n[{i}/{len(section_order)}] Processing {section}...")
            
            if section not in self.sections:
                print(f"⚠️  WARNING: Section '{section}' not found, skipping")
                continue
            
            result = self.run_section(section, dry_run=False)
            if result != 0:
                print(f"❌ Failed at section {section}")
                return result
        
        print("\n✅ All sections completed successfully!")
        return 0
    
    def run_schema_only(self, schema_name: str, dry_run: bool = True) -> int:
        """Recreate a single schema (useful for refreshing demo/live_masked)"""
        
        # Validate schema name
        allowed_schemas = ['demo', 'live_masked']
        if schema_name == 'live':
            print("⚠️  WARNING: Recreating 'live' schema will destroy authentication data!")
            response = input("   Are you REALLY sure? Type 'yes-destroy-auth': ")
            if response != 'yes-destroy-auth':
                print("❌ Cancelled")
                return 1
            allowed_schemas.append('live')
        elif schema_name not in allowed_schemas:
            print(f"❌ ERROR: Schema '{schema_name}' not allowed")
            print(f"   Allowed schemas: {', '.join(allowed_schemas)}")
            return 1
        
        section_name = f"SCHEMA:{schema_name}"
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Would recreate schema: {schema_name}")
            print("   This will:")
            print(f"   • DROP SCHEMA {schema_name} CASCADE (⚠️  DATA LOSS)")
            print(f"   • CREATE SCHEMA {schema_name}")
            print("   • Create all tables")
            print("   • Insert reference data")
            print("\n💡 To execute, run with --no-dry-run")
            return 0
        
        print(f"\n🚀 Recreating schema: {schema_name}")
        
        # Run the schema section
        result = self.run_section(section_name, dry_run=False)
        
        if result == 0:
            # Also run permissions section to ensure permissions are set
            print("\n📝 Refreshing permissions...")
            self.run_section('PERMISSIONS', dry_run=False)
            print(f"✅ Schema {schema_name} recreated successfully!")
        
        return result

def main():
    parser = argparse.ArgumentParser(
        description='Setup BAIS database schema as rc34924',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available sections
  python bais_database_schema.py --list
  
  # Dry run all sections (default)
  python bais_database_schema.py
  
  # Execute all sections
  python bais_database_schema.py --no-dry-run
  
  # Run specific section
  python bais_database_schema.py --section USER_CREATION --no-dry-run
  python bais_database_schema.py --section SCHEMA:live --no-dry-run
  
  # Recreate a single schema (useful for refresh)
  python bais_database_schema.py --recreate-schema demo --no-dry-run
  python bais_database_schema.py --recreate-schema live_masked --no-dry-run
  
Environment variables required:
  POSTGRESQL_BAIS_DB_ADMIN_URL or individual components:
  - POSTGRESQL_INSTANCE_HOST (default: 0.0.0.0)
  - POSTGRESQL_INSTANCE_PORT (default: 5432)
  - POSTGRESQL_BAIS_DB_ADMIN_USER (default: rc34924)
  - POSTGRESQL_BAIS_DB_ADMIN_PASSWORD
  - POSTGRESQL_BAIS_DB (default: prutech_bais)
        """
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available sections'
    )
    
    parser.add_argument(
        '--section',
        type=str,
        help='Run a specific section'
    )
    
    parser.add_argument(
        '--recreate-schema',
        type=str,
        choices=['demo', 'live_masked', 'live'],
        help='Recreate a single schema (demo or live_masked typically)'
    )
    
    parser.add_argument(
        '--no-dry-run',
        action='store_true',
        help='Actually execute SQL (default is dry-run)'
    )
    
    args = parser.parse_args()
    
    # Initialize manager
    try:
        manager = BaisSchemaManager()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    
    # Handle list option
    if args.list:
        manager.list_sections()
        sys.exit(0)
    
    # Determine what to run
    dry_run = not args.no_dry_run
    
    if args.recreate_schema:
        # Recreate single schema
        if dry_run:
            sys.exit(manager.run_schema_only(args.recreate_schema, dry_run=True))
        
        print(f"⚠️  WARNING: This will DROP and recreate schema '{args.recreate_schema}'")
        print("   All data in this schema will be PERMANENTLY DELETED.")
        response = input("\n   Type 'yes' to continue: ")
        
        if response.lower() != 'yes':
            print("❌ Cancelled by user")
            sys.exit(1)
        
        sys.exit(manager.run_schema_only(args.recreate_schema, dry_run=False))
    
    elif args.section:
        # Run specific section
        if dry_run:
            sys.exit(manager.run_section(args.section, dry_run=True))
        
        if args.section.startswith('SCHEMA:'):
            schema_name = args.section.split(':')[1]
            print(f"⚠️  WARNING: This will DROP and recreate schema '{schema_name}'")
            print("   All data in this schema will be PERMANENTLY DELETED.")
            response = input("\n   Type 'yes' to continue: ")
            
            if response.lower() != 'yes':
                print("❌ Cancelled by user")
                sys.exit(1)
        
        sys.exit(manager.run_section(args.section, dry_run=False))
    
    else:
        # Run all sections
        if dry_run:
            sys.exit(manager.run_all(dry_run=True))
        
        print("⚠️  WARNING: This will DROP and recreate ALL schemas")
        print("   All data will be PERMANENTLY DELETED.")
        response = input("\n   Type 'yes' to continue: ")
        
        if response.lower() != 'yes':
            print("❌ Cancelled by user")
            sys.exit(1)
        
        sys.exit(manager.run_all(dry_run=False))

if __name__ == '__main__':
    main()
