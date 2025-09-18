#!/usr/bin/env python3
"""
Script: recreate_schemas_refresh_users.py
Purpose: Recreate specific schemas while preserving database and users
         Can optionally refresh all user permissions to match the original design

This script:
  - Preserves database and users (never drops them)
  - Drops and recreates only specified schemas
  - Reloads reference data and creates empty tables
  - Optionally refreshes all permissions to original specifications
  - READS ALL SQL FROM bais_database_schema.sql (no hardcoded SQL)

Usage:
  python recreate_schemas_refresh_users.py --recreate-schemas demo              # Dry run for demo schema
  python recreate_schemas_refresh_users.py --recreate-schemas demo,live_masked  # Dry run for multiple
  python recreate_schemas_refresh_users.py --recreate-schemas demo --no-dry-run # Execute with confirmation
  python recreate_schemas_refresh_users.py --recreate-schemas demo --refresh-permissions  # Also refresh permissions
  
Requires: Admin database credentials (rc34924)
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from pathlib import Path
import re

def extract_sql_section(sql_content, section_name):
    """Extract a specific section from the SQL file based on section markers"""
    # Pattern to match section content between markers
    pattern = rf'-- ==================== SECTION: {re.escape(section_name)} ====================\n(.*?)\n-- ==================== END SECTION: {re.escape(section_name)} ===================='
    
    match = re.search(pattern, sql_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        raise ValueError(f"Section '{section_name}' not found in SQL file")

def validate_schemas(requested_schemas, allowed_schemas):
    """Validate requested schemas against allowed list from .env"""
    requested_set = set(s.strip() for s in requested_schemas.split(','))
    allowed_set = set(s.strip() for s in allowed_schemas.split(','))
    
    invalid = requested_set - allowed_set
    if invalid:
        return False, f"Schemas not allowed for recreation: {', '.join(invalid)}"
    
    return True, list(requested_set)

def main():
    parser = argparse.ArgumentParser(
        description="Recreate specific schemas while preserving database and users",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--recreate-schemas', required=True,
          help='Comma-separated list of allowed schemas (in .env) to recreate (e.g., demo,live_masked)')
    parser.add_argument('--no-dry-run', action='store_true',
          help='Actually execute the recreation (default is dry run)')
    parser.add_argument('--refresh-permissions', action='store_true',
          help='Also refresh all user permissions to original specifications')
    
    args = parser.parse_args()
    dry_run = not args.no_dry_run
    
    # Header
    print("=" * 70)
    print("🔄 BAIS SCHEMA RECREATION")
    print("=" * 70)
    
    # Load environment variables
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    if not env_path.exists():
        print(f"\n❌ ERROR: .env file not found at {env_path}")
        print("   This file must exist and contain ALLOWED_SCHEMA_RECREATE")
        sys.exit(1)
    
    load_dotenv(env_path)
    
    # Get allowed schemas from .env
    allowed_schemas = os.getenv('ALLOWED_SCHEMA_RECREATE')
    if not allowed_schemas:
        print("\n❌ ERROR: ALLOWED_SCHEMA_RECREATE not set in .env file")
        print("   Add: ALLOWED_SCHEMA_RECREATE=demo,live_masked")
        print("   (Never include 'live' unless you really want to recreate auth tables!)")
        sys.exit(1)
    
    # Validate requested schemas
    valid, result = validate_schemas(args.recreate_schemas, allowed_schemas)
    if not valid:
        print(f"\n❌ ERROR: {result}")
        print(f"   Allowed schemas from .env: {allowed_schemas}")
        sys.exit(1)
    
    schemas_to_recreate = result
    
    # Get database credentials
    pg_host = os.getenv('POSTGRESQL_INSTANCE_HOST', 'localhost')
    pg_port = os.getenv('POSTGRESQL_INSTANCE_PORT', '5432')
    bais_db = os.getenv('POSTGRESQL_BAIS_DB', 'prutech_bais')
    admin_user = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_USER', 'rc34924')
    admin_password = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_PASSWORD')
    
    if not admin_password:
        print("\n❌ ERROR: Admin password not set in .env file")
        sys.exit(1)
    
    # Load the SQL file
    sql_file_path = Path(__file__).parent.parent.parent / 'database' / 'bais_database_schema.sql'
    if not sql_file_path.exists():
        print(f"\n❌ ERROR: SQL file not found: {sql_file_path}")
        sys.exit(1)
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    print(f"\n📋 Configuration:")
    print(f"   🖥️  Host: {pg_host}:{pg_port}")
    print(f"   🗄️  Database: {bais_db}")
    print(f"   👤 Admin User: {admin_user}")
    print(f"   📄 SQL File: {sql_file_path.name}")
    print(f"   📂 Schemas to recreate: {', '.join(schemas_to_recreate)}")
    if args.refresh_permissions:
        print(f"   🔐 Will refresh permissions: Yes")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - Showing what would happen")
        print("💡 Use --no-dry-run to actually execute")
    else:
        print("\n⚠️  EXECUTION MODE - This will DROP and recreate schemas!")
        print(f"⚠️  Schemas to be destroyed: {', '.join(schemas_to_recreate)}")
        print("⚠️  All data in these schemas WILL BE LOST!")
        
        response = input("\n⚠️  Are you sure? Type 'Yes' or 'yes' to continue: ")
        if response not in ['Yes', 'yes']:
            print("❌ Aborted - no action taken")
            sys.exit(0)
    
    try:
        # Connect as admin
        print(f"\n🔌 Connecting to {bais_db} as {admin_user}...")
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=bais_db,
            user=admin_user,
            password=admin_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        print("✅ Connected successfully")
        
        # Check current status
        print("\n📊 Current Status:")
        for schema in schemas_to_recreate:
            # Use pg_tables for accurate count
            cur.execute("""
                SELECT COUNT(*) FROM pg_tables 
                WHERE schemaname = %s
            """, (schema,))
            table_count = cur.fetchone()[0]
            print(f"   Schema '{schema}': {table_count} tables")
        
        # Extract necessary SQL sections
        # NOTE: Prerequisites should already exist from nuclear reset
        # rc34924 can't CREATE OR REPLACE functions owned by postgres
        # This is a design issue documented in SQL_REWRITE_NOTES.md
        prerequisites_sql = None  # Skip prerequisites - they should exist
        
        # Phase 1: Drop schemas
        print("\n" + "=" * 70)
        print("💥 DESTRUCTION PHASE")
        print("=" * 70)
        
        for schema in schemas_to_recreate:
            if dry_run:
                print(f"🔍 DRY RUN: Would drop schema {schema} CASCADE")
            else:
                print(f"⚡ Dropping schema {schema} CASCADE...")
                cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
                print(f"✅ Schema {schema} dropped")
        
        # Phase 2: Ensure prerequisites exist
        if prerequisites_sql and not dry_run:
            print("\n" + "=" * 70)
            print("🔧 PREREQUISITES PHASE")
            print("=" * 70)
            print("⚡ Ensuring database prerequisites...")
            cur.execute(prerequisites_sql)
            print("✅ Prerequisites ensured")
        
        # Phase 3: Recreate schemas
        print("\n" + "=" * 70)
        print("🏗️  RECREATION PHASE")
        print("=" * 70)
        
        for schema in schemas_to_recreate:
            if dry_run:
                print(f"\n🔍 DRY RUN: Would recreate schema {schema}")
                print(f"   • Extract and execute SCHEMA:{schema} section from SQL file")
                print(f"   • Create schema and grant permissions")
                print(f"   • Create reference tables with seed data")
                print(f"   • Create business tables (empty)")
                if schema == 'live':
                    print(f"   • Create auth tables with roles")
                print(f"   • Create indexes and triggers")
            else:
                print(f"\n⚡ Recreating schema {schema}...")
                
                # Extract and execute the schema section
                try:
                    schema_sql = extract_sql_section(sql_content, f'SCHEMA:{schema}')
                    cur.execute(schema_sql)
                    
                    print(f"✅ Schema {schema} recreated with:")
                    print(f"   • Reference tables with seed data")
                    print(f"   • Business tables (empty)")
                    if schema == 'live':
                        print(f"   • Auth tables with roles (no users)")
                except ValueError as e:
                    print(f"❌ Error: {e}")
                    sys.exit(1)
                except psycopg2.Error as e:
                    print(f"❌ PostgreSQL Error: {e}")
                    sys.exit(1)
        
        # Phase 4: Refresh permissions (if requested)
        if args.refresh_permissions:
            print("\n" + "=" * 70)
            print("🔐 PERMISSION REFRESH")
            print("=" * 70)
            
            if dry_run:
                print("🔍 DRY RUN: Would refresh all permissions")
                print("   • Extract and execute PERMISSIONS section from SQL file")
                print("   • bais_ro: SELECT on all tables")
                print("   • bais_rw: Three-tier model permissions")
            else:
                print("⚡ Refreshing all user permissions...")
                try:
                    permissions_sql = extract_sql_section(sql_content, 'PERMISSIONS')
                    cur.execute(permissions_sql)
                    print("✅ Permissions refreshed to original specifications")
                except ValueError as e:
                    print(f"❌ Error: {e}")
                    sys.exit(1)
                except psycopg2.Error as e:
                    print(f"❌ PostgreSQL Error: {e}")
                    sys.exit(1)
        
        # Verify
        if not dry_run:
            print("\n📊 Verification:")
            for schema in schemas_to_recreate:
                # Use pg_tables for accurate count
                cur.execute("""
                    SELECT COUNT(*) FROM pg_tables 
                    WHERE schemaname = %s
                """, (schema,))
                table_count = cur.fetchone()[0]
                print(f"   Schema '{schema}': {table_count} tables recreated")
        
        cur.close()
        conn.close()
        
        # Summary
        print("\n" + "=" * 70)
        if dry_run:
            print("🔍 DRY RUN COMPLETED - No changes were made")
        else:
            print("🎉 SCHEMA RECREATION COMPLETED!")
        print("=" * 70)
        
        print("\n📋 Summary:")
        print(f"   📂 Schemas recreated: {', '.join(schemas_to_recreate)}")
        print("   📊 Tables: Reference tables with data, business tables empty")
        print("   📄 All SQL read from: bais_database_schema.sql")
        if args.refresh_permissions and not dry_run:
            print("   🔐 Permissions: Refreshed to original specifications")
        
        if dry_run:
            print("\n🔍 This was a DRY RUN - no changes were made!")
            print("💡 Use --no-dry-run to actually recreate schemas")
        
    except psycopg2.Error as e:
        print(f"\n❌ PostgreSQL Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
