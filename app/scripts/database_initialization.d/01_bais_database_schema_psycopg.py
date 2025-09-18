#!/usr/bin/env python3
"""
BAIS Database Schema Script (psycopg3 version)
==============================================
Purpose: Setup complete BAIS database schema using psycopg3
Executes as: rc34924 (BAIS admin user)

This is a pure Python version that doesn't require psql binary.
Functionality is identical to bais_database_schema.py.

This script creates:
- Service users (bais_ro, bais_rw)
- Shared functions
- All three schemas (live, live_masked, demo)
- All tables and permissions

Usage:
    # Run everything
    python bais_database_schema_psycopg.py --no-dry-run
    
    # Run specific sections
    python bais_database_schema_psycopg.py --section USER_CREATION --no-dry-run
    python bais_database_schema_psycopg.py --section SCHEMA:live --no-dry-run
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

try:
    import psycopg
    from psycopg import sql
except ImportError:
    print("❌ ERROR: psycopg3 not installed. Run: pip install 'psycopg[binary]'")
    sys.exit(1)

# Load environment variables from .env file
env_file = Path(__file__).parent.parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"✓ Loaded environment from {env_file}")
else:
    print(f"⚠️  No .env file found at {env_file}, using system environment")

class BaisSchemaManagerPsycopg:
    """Manages BAIS database schema setup using psycopg3"""
    
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
    
    def get_connection_params(self) -> Dict[str, str]:
        """Get rc34924 connection parameters from environment"""
        # Try complete URL first
        url = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_URL')
        if url:
            # Parse connection URL
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            return {
                'host': parsed.hostname or '0.0.0.0',
                'port': parsed.port or 5432,
                'user': parsed.username or 'rc34924',
                'password': parsed.password or '',
                'dbname': parsed.path.lstrip('/') if parsed.path else 'prutech_bais'
            }
        
        # Build from components
        return {
            'host': os.getenv('POSTGRESQL_INSTANCE_HOST', '0.0.0.0'),
            'port': int(os.getenv('POSTGRESQL_INSTANCE_PORT', '5432')),
            'user': os.getenv('POSTGRESQL_BAIS_DB_ADMIN_USER', 'rc34924'),
            'password': os.getenv('POSTGRESQL_BAIS_DB_ADMIN_PASSWORD', 'cBmVWgt8uzvyKj54x3E4Tn6s'),
            'dbname': os.getenv('POSTGRESQL_BAIS_DB', 'prutech_bais')
        }
    
    def list_sections(self):
        """List available sections"""
        print("\n📚 Available sections:")
        for name in self.sections:
            if name.startswith('SCHEMA:'):
                print(f"   • {name} (schema creation)")
            else:
                print(f"   • {name}")
    
    def split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements"""
        # Handle DO blocks specially - they contain semicolons but are one statement
        statements = []
        
        # Check if this contains dollar-quoted blocks (DO blocks or functions)
        if '$$' in sql_content:
            # Handle dollar-quoted sections as single statements
            current_pos = 0
            content = sql_content
            
            while current_pos < len(content):
                # Find next $$
                dollar_start = content.find('$$', current_pos)
                
                if dollar_start == -1:
                    # No more dollar quotes - process remainder
                    remaining = content[current_pos:].strip()
                    if remaining:
                        for stmt in self._split_regular_sql(remaining):
                            if stmt:
                                statements.append(stmt)
                    break
                
                # Process SQL before the $$
                before = content[current_pos:dollar_start].strip()
                if before and not before.endswith('AS') and not before.endswith('DO'):
                    for stmt in self._split_regular_sql(before):
                        if stmt:
                            statements.append(stmt)
                
                # Find the matching closing $$
                # Look backwards from $$ to find the statement start
                stmt_start = current_pos
                for keyword in ['CREATE', 'DO', 'DECLARE']:
                    idx = content.rfind(keyword, current_pos, dollar_start)
                    if idx != -1:
                        stmt_start = idx
                        break
                
                # Find the ending $$ and semicolon
                dollar_end = content.find('$$', dollar_start + 2)
                if dollar_end != -1:
                    # Look for the statement-ending semicolon
                    semi = content.find(';', dollar_end + 2)
                    if semi != -1:
                        # Include the full statement
                        full_stmt = content[stmt_start:semi + 1].strip()
                        if full_stmt:
                            statements.append(full_stmt)
                        current_pos = semi + 1
                    else:
                        # No semicolon found - take to end
                        full_stmt = content[stmt_start:].strip()
                        if full_stmt:
                            statements.append(full_stmt)
                        break
                else:
                    # No closing $$ found - error but try to continue
                    current_pos = len(content)
        else:
            # No DO blocks - regular splitting
            statements = self._split_regular_sql(sql_content)
        
        return statements
    
    def _split_regular_sql(self, sql_content: str) -> List[str]:
        """Split regular SQL (not DO blocks) into statements"""
        # Remove comments (but keep section markers for reference)
        lines = []
        for line in sql_content.split('\n'):
            # Skip comment lines (but not section markers)
            if line.strip().startswith('--') and not line.strip().startswith('-- ===='):
                continue
            lines.append(line)
        
        # Join and split by semicolons
        content = '\n'.join(lines)
        
        # Split by semicolon but not within strings
        statements = []
        current = []
        in_string = False
        escape_next = False
        
        for char in content:
            if escape_next:
                current.append(char)
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                current.append(char)
                continue
            
            if char == "'" and not escape_next:
                in_string = not in_string
            
            if char == ';' and not in_string:
                stmt = ''.join(current).strip()
                if stmt:  # Skip empty statements
                    statements.append(stmt)
                current = []
            else:
                current.append(char)
        
        # Add any remaining statement
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)
        
        return statements
    
    def execute_statements(self, conn, statements: List[str], description: str, dry_run: bool = True) -> Tuple[int, int, int]:
        """Execute a list of SQL statements and return counts"""
        if dry_run:
            print(f"\n🔍 DRY RUN - Would execute: {description}")
            preview_lines = []
            for i, stmt in enumerate(statements[:3], 1):
                # Truncate long statements for preview
                preview = stmt[:100] + '...' if len(stmt) > 100 else stmt
                preview_lines.append(f"   {i}. {preview}")
            
            print('\n'.join(preview_lines))
            if len(statements) > 3:
                print(f"   ... and {len(statements) - 3} more statements")
            return 0, 0, 0
        
        creates = 0
        grants = 0  
        inserts = 0
        
        with conn.cursor() as cur:
            for stmt in statements:
                try:
                    cur.execute(stmt)
                    
                    # Count operation types
                    stmt_upper = stmt.upper()
                    if 'CREATE' in stmt_upper:
                        creates += 1
                    elif 'GRANT' in stmt_upper:
                        grants += 1
                    elif 'INSERT' in stmt_upper:
                        inserts += 1
                        
                except psycopg.errors.DuplicateObject:
                    # Object already exists - that's ok for idempotency
                    pass
                except psycopg.errors.DuplicateDatabase:
                    # Database already exists
                    pass
                except psycopg.errors.DuplicateTable:
                    # Table already exists
                    pass
                except Exception as e:
                    print(f"❌ ERROR executing statement: {e}")
                    print(f"   Statement: {stmt[:100]}...")
                    raise
        
        conn.commit()
        return creates, grants, inserts
    
    def execute_sql(self, sql_content: str, description: str, dry_run: bool = True) -> int:
        """Execute SQL content via psycopg3"""
        
        # If content has dollar quotes, execute as single statement
        if '$$' in sql_content:
            statements = [sql_content.strip()]
        else:
            statements = self.split_sql_statements(sql_content)
        
        if not statements:
            print(f"⚠️  No SQL statements found in: {description}")
            return 0
        
        if dry_run:
            print(f"\n🔍 DRY RUN - Would execute: {description}")
            print(f"   {len(statements)} SQL statements to execute")
            return 0
        
        print(f"\n🚀 Executing: {description}")
        
        try:
            params = self.get_connection_params()
            with psycopg.connect(**params) as conn:
                # Special handling for sections with dollar quotes
                if '$$' in sql_content:
                    with conn.cursor() as cur:
                        try:
                            cur.execute(sql_content)
                            conn.commit()
                            print(f"   ✓ Section executed successfully")
                            return 0
                        except Exception as e:
                            print(f"❌ ERROR executing section: {e}")
                            return 1
                else:
                    creates, grants, inserts = self.execute_statements(
                        conn, statements, description, dry_run=False
                    )
                    
                    # Report results
                    if creates > 0:
                        print(f"   ✓ {creates} objects created")
                    if grants > 0:
                        print(f"   ✓ {grants} permissions granted")
                    if inserts > 0:
                        print(f"   ✓ {inserts} data rows inserted")
                    
                    return 0
                
        except psycopg.OperationalError as e:
            print(f"❌ ERROR: Could not connect to database: {e}")
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
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            params = self.get_connection_params()
            with psycopg.connect(**params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT current_user, current_database()")
                    user, database = cur.fetchone()
                    print(f"✅ Connected as {user} to {database}")
                    return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Setup BAIS database schema using psycopg3 (no psql required)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This is a pure Python version that doesn't require the psql binary.
Functionality is identical to bais_database_schema.py.

Examples:
  # Test connection
  python bais_database_schema_psycopg.py --test
  
  # List available sections
  python bais_database_schema_psycopg.py --list
  
  # Dry run all sections (default)
  python bais_database_schema_psycopg.py
  
  # Execute all sections
  python bais_database_schema_psycopg.py --no-dry-run
  
  # Run specific section
  python bais_database_schema_psycopg.py --section USER_CREATION --no-dry-run
  python bais_database_schema_psycopg.py --section SCHEMA:live --no-dry-run
  
  # Recreate a single schema (useful for refresh)
  python bais_database_schema_psycopg.py --recreate-schema demo --no-dry-run
  python bais_database_schema_psycopg.py --recreate-schema live_masked --no-dry-run
  
Environment variables loaded from .env file or system:
  POSTGRESQL_BAIS_DB_ADMIN_URL or individual components:
  - POSTGRESQL_INSTANCE_HOST (default: 0.0.0.0)
  - POSTGRESQL_INSTANCE_PORT (default: 5432)
  - POSTGRESQL_BAIS_DB_ADMIN_USER (default: rc34924)
  - POSTGRESQL_BAIS_DB_ADMIN_PASSWORD
  - POSTGRESQL_BAIS_DB (default: prutech_bais)
        """
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test database connection'
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
        manager = BaisSchemaManagerPsycopg()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    
    # Handle test connection
    if args.test:
        sys.exit(0 if manager.test_connection() else 1)
    
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
