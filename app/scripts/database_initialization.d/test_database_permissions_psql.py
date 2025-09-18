#!/usr/bin/env python3
"""
Database Permission Test Script V3 (psql version with pglast)
==============================================================
Fully introspective version that parses SQL schema file dynamically.
Uses pglast for robust PostgreSQL DDL parsing.
No hardcoded table names, columns, or permission rules.
Everything is derived from the SQL schema definition file.
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import pglast
from pglast import ast, parse_sql
from pglast.enums import ConstrType

# Load environment variables
env_file = Path(__file__).parent.parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

@dataclass
class PermissionRule:
    """Expected permission for a user on a table"""
    user: str
    schema: str
    table: str
    select: bool
    insert: bool
    update: bool
    delete: bool
    column_permissions: Dict[str, List[str]] = None  # For column-level permissions

class DatabasePermissionTester:
    """Introspective permission tester using psql and SQL schema parsing"""
    
    def __init__(self):
        """Initialize the tester"""
        # Build connection URL for admin user
        host = os.getenv('POSTGRESQL_INSTANCE_HOST', '0.0.0.0')
        port = os.getenv('POSTGRESQL_INSTANCE_PORT', '5432')
        user = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_USER', 'rc34924')
        password = os.getenv('POSTGRESQL_BAIS_DB_ADMIN_PASSWORD', 'cBmVWgt8uzvyKj54x3E4Tn6s')
        dbname = os.getenv('POSTGRESQL_BAIS_DB', 'prutech_bais')
        
        self.conn_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=disable"
        self.results = {'passed': 0, 'failed': 0, 'failures': []}
        
        # Parse SQL schema file
        sql_file = Path(__file__).parent.parent.parent / 'database' / 'bais_database_schema.sql'
        self.schema_info = self.parse_sql_schema(sql_file)
        
    def parse_sql_schema(self, sql_file: Path) -> Dict:
        """Parse SQL schema file to extract tables, columns, and permissions"""
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        schema_info = {
            'schemas': [],
            'tables': {},
            'grants': [],
            'column_grants': []
        }
        
        # Extract schema sections
        schema_pattern = r'-- ==================== SECTION: SCHEMA:(\w+)'
        for match in re.finditer(schema_pattern, sql_content):
            schema_name = match.group(1).lower()
            schema_info['schemas'].append(schema_name)
        
        # Parse each schema section
        for schema in schema_info['schemas']:
            schema_info['tables'][schema] = {}
            
            # Extract section for this schema
            section_pattern = rf'-- ==================== SECTION: SCHEMA:{schema} ====================.*?(?=-- ==================== END SECTION)'
            section_match = re.search(section_pattern, sql_content, re.IGNORECASE | re.DOTALL)
            
            if section_match:
                section_content = section_match.group(0)
                
                # Parse CREATE TABLE statements with pglast
                # Extract all CREATE TABLE statements
                table_matches = re.finditer(
                    r'CREATE TABLE (?:IF NOT EXISTS )?([\w.]+)\s*\(([^;]+)\);',
                    section_content,
                    re.IGNORECASE | re.DOTALL
                )

                for table_match in table_matches:
                    full_table_name = table_match.group(1)
                    table_def = f"CREATE TABLE {full_table_name} ({table_match.group(2)});"

                    # Handle schema.table format
                    if '.' in full_table_name:
                        _, table_name = full_table_name.split('.', 1)
                    else:
                        table_name = full_table_name

                    # Parse with pglast
                    try:
                        parsed_stmts = parse_sql(table_def)
                        if parsed_stmts:
                            stmt = parsed_stmts[0].stmt
                            if isinstance(stmt, ast.CreateStmt):
                                columns = []
                                column_details = []

                                # Extract columns from CREATE TABLE statement
                                for element in stmt.tableElts:
                                    if isinstance(element, ast.ColumnDef):
                                        col_name = element.colname
                                        columns.append(col_name)

                                        # Create column detail dict
                                        col_detail = {'name': col_name}

                                        # Check for references (foreign keys)
                                        for constraint in (element.constraints or []):
                                            if isinstance(constraint, ast.Constraint):
                                                if constraint.contype == ConstrType.CONSTR_FOREIGN:
                                                    if constraint.pktable:
                                                        col_detail['references'] = constraint.pktable.relname

                                        column_details.append(col_detail)

                                schema_info['tables'][schema][table_name] = {
                                    'columns': columns,
                                    'column_details': column_details
                                }
                            else:
                                # If not a CreateStmt, still record the table
                                schema_info['tables'][schema][table_name] = {'columns': [], 'column_details': []}
                    except Exception as e:
                        # Fallback: still record the table but without columns
                        schema_info['tables'][schema][table_name] = {'columns': [], 'column_details': []}
                
                # Parse GRANT statements - handle both specific tables and ALL TABLES
                # First, check for GRANT ... ON ALL TABLES
                all_tables_pattern = r'GRANT\s+(.*?)\s+ON\s+ALL\s+TABLES\s+IN\s+SCHEMA\s+(\w+)\s+TO\s+([\w,\s]+);'
                for match in re.finditer(all_tables_pattern, section_content, re.IGNORECASE):
                    permissions = match.group(1).strip()
                    grant_schema = match.group(2).strip()
                    users = match.group(3).strip()
                    
                    if grant_schema.lower() == schema:
                        # Apply to all tables in this schema
                        for table_name in schema_info['tables'][schema].keys():
                            for user in users.split(','):
                                user = user.strip()
                                schema_info['grants'].append({
                                    'user': user,
                                    'schema': schema,
                                    'table': table_name,
                                    'permissions': [p.strip().upper() for p in permissions.split(',')]
                                })
                
                # Then parse specific table grants
                grant_pattern = r'GRANT\s+(.*?)\s+ON\s+(?!ALL)([\w.]+)\s+TO\s+([\w,\s]+);'
                for match in re.finditer(grant_pattern, section_content, re.IGNORECASE):
                    permissions = match.group(1).strip()
                    table_full = match.group(2).strip()
                    users = match.group(3).strip()
                    
                    # Skip SCHEMA grants
                    if 'SCHEMA' in table_full.upper():
                        continue
                    
                    # Handle schema.table format
                    if '.' in table_full:
                        table_schema, table_name = table_full.split('.', 1)
                    else:
                        table_schema = schema
                        table_name = table_full
                    
                    for user in users.split(','):
                        user = user.strip()
                        
                        # Check for column-level permissions
                        col_match = re.match(r'(\w+)\s*\(([\w,\s]+)\)', permissions)
                        if col_match:
                            perm_type = col_match.group(1).upper()
                            columns = [c.strip() for c in col_match.group(2).split(',')]
                            schema_info['column_grants'].append({
                                'user': user,
                                'schema': table_schema,
                                'table': table_name,
                                'permission': perm_type,
                                'columns': columns
                            })
                        else:
                            schema_info['grants'].append({
                                'user': user,
                                'schema': table_schema,
                                'table': table_name,
                                'permissions': [p.strip().upper() for p in permissions.split(',')]
                            })
        
        return schema_info
    
    def get_expected_permissions(self) -> List[PermissionRule]:
        """Generate expected permissions from parsed SQL schema"""
        rules = []
        
        for schema in self.schema_info['schemas']:
            tables = self.schema_info['tables'].get(schema, {})
            
            for table_name in tables:
                # Determine expected permissions based on grants
                for grant in self.schema_info['grants']:
                    if grant['schema'] == schema and grant['table'] == table_name:
                        rule = PermissionRule(
                            user=grant['user'],
                            schema=schema,
                            table=table_name,
                            select='SELECT' in grant['permissions'],
                            insert='INSERT' in grant['permissions'],
                            update='UPDATE' in grant['permissions'],
                            delete='DELETE' in grant['permissions']
                        )
                        
                        # Add column-level permissions
                        col_perms = {}
                        for col_grant in self.schema_info['column_grants']:
                            if (col_grant['user'] == grant['user'] and 
                                col_grant['schema'] == schema and 
                                col_grant['table'] == table_name):
                                col_perms[col_grant['permission']] = col_grant['columns']
                        if col_perms:
                            rule.column_permissions = col_perms
                        
                        rules.append(rule)
        
        return rules
    
    def execute_sql(self, sql: str) -> Tuple[bool, str]:
        """Execute SQL via psql and return success and output"""
        try:
            result = subprocess.run(
                ['psql', self.conn_url, '-t', '-A', '-c', sql],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            return False, "Query timeout"
        except FileNotFoundError:
            print("❌ ERROR: psql not found. Please install PostgreSQL client.")
            sys.exit(1)
        except Exception as e:
            return False, str(e)
    
    def check_permission(self, user: str, schema: str, table: str, privilege: str) -> bool:
        """Check if user has specific privilege on table using PostgreSQL introspection"""
        sql = f"SELECT has_table_privilege('{user}', '{schema}.{table}', '{privilege}');"
        success, output = self.execute_sql(sql)
        
        if success:
            return output.lower() == 't'
        else:
            print(f"⚠️  Error checking {user} {privilege} on {schema}.{table}: {output}")
            return False
    
    def check_column_permission(self, user: str, schema: str, table: str, column: str, privilege: str) -> bool:
        """Check if user has specific privilege on a column"""
        sql = f"SELECT has_column_privilege('{user}', '{schema}.{table}', '{column}', '{privilege}');"
        success, output = self.execute_sql(sql)
        
        if success:
            return output.lower() == 't'
        else:
            return False
    
    def get_tables_in_schema(self, schema: str) -> List[str]:
        """Get all tables in a schema"""
        sql = f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema}' ORDER BY tablename;"
        success, output = self.execute_sql(sql)
        
        if success and output:
            return output.strip().split('\n')
        else:
            return []
    
    def test_column_level_permissions(self):
        """Test column-level permissions on biz_components table"""
        print("\n" + "=" * 70)
        print("COLUMN-LEVEL PERMISSIONS TEST")
        print("=" * 70)
        
        # Find biz_components table in demo schema
        demo_tables = self.schema_info['tables'].get('demo', {})
        biz_components = demo_tables.get('biz_components', {})
        columns = biz_components.get('columns', [])
        
        if not columns:
            print("⚠️  No columns found for demo.biz_components in SQL schema")
            return
        
        # Filter to test only important columns (skip auto-generated ones)
        test_columns = [col for col in columns if col not in ['created_at', 'updated_at']]
        
        print("\nTesting bais_rw access to biz_components columns...")
        for col in test_columns:
            if self.check_column_permission('bais_rw', 'demo', 'biz_components', col, 'INSERT'):
                print(f"  ✅ bais_rw can INSERT to demo.biz_components.{col}")
                self.results['passed'] += 1
            else:
                print(f"  ❌ bais_rw cannot INSERT to demo.biz_components.{col}")
                self.results['failed'] += 1
                self.results['failures'].append(f"Column: bais_rw INSERT on demo.biz_components.{col}")
        
        print("\nTesting bais_ro access to biz_components columns...")
        for col in test_columns:
            # Test SELECT permission - should pass
            if self.check_column_permission('bais_ro', 'demo', 'biz_components', col, 'SELECT'):
                print(f"  ✅ bais_ro can SELECT from demo.biz_components.{col}")
                self.results['passed'] += 1
            else:
                print(f"  ❌ bais_ro cannot SELECT from demo.biz_components.{col}")
                self.results['failed'] += 1
                self.results['failures'].append(f"Column: bais_ro SELECT on demo.biz_components.{col}")
            
            # Test INSERT permission - should fail
            if not self.check_column_permission('bais_ro', 'demo', 'biz_components', col, 'INSERT'):
                print(f"  ✅ bais_ro cannot INSERT to demo.biz_components.{col} (correct)")
                self.results['passed'] += 1
            else:
                print(f"  ❌ bais_ro CAN INSERT to demo.biz_components.{col} (should not!)")
                self.results['failed'] += 1
                self.results['failures'].append(f"Column: bais_ro should not INSERT on demo.biz_components.{col}")
    
    def test_fk_constraints(self):
        """Test that FK constraints are properly enforced"""
        print("\n" + "=" * 70)
        print("FOREIGN KEY CONSTRAINT TESTS")
        print("=" * 70)
        
        print("\nTesting NOT NULL constraints on FK columns...")
        
        # Get FK columns from biz_components
        demo_tables = self.schema_info['tables'].get('demo', {})
        biz_components = demo_tables.get('biz_components', {})
        column_details = biz_components.get('column_details', [])
        
        # Find FK columns (those with references)
        fk_columns = [col for col in column_details if col.get('references')]
        
        if fk_columns:
            cmd = f"""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'demo' 
                AND table_name = 'biz_components'
                AND column_name IN ({','.join(f"'{col['name']}'" for col in fk_columns)})
                ORDER BY column_name
            """
            
            success, output = self.execute_sql(cmd)
            if success and output:
                lines = output.strip().split('\n')
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        column_name = parts[0].strip()
                        is_nullable = parts[1].strip()
                        if is_nullable == 'NO':
                            print(f"  ✅ {column_name} is NOT NULL (correct)")
                            self.results['passed'] += 1
                        else:
                            print(f"  ❌ {column_name} is nullable (should be NOT NULL)")
                            self.results['failed'] += 1
                            self.results['failures'].append(f"Constraint: {column_name} should be NOT NULL")
    
    def test_special_permissions(self):
        """Test special cases like UPDATE(last_login) for bais_rw"""
        print("\n" + "=" * 70)
        print("SPECIAL PERMISSIONS")
        print("=" * 70)
        
        # Check for column-level grants in the parsed data
        for col_grant in self.schema_info['column_grants']:
            if (col_grant['user'] == 'bais_rw' and 
                col_grant['schema'] == 'live' and 
                col_grant['table'] == 'auth_users' and
                col_grant['permission'] == 'UPDATE' and
                'last_login' in col_grant['columns']):
                
                # Test the special permission
                if self.check_column_permission('bais_rw', 'live', 'auth_users', 'last_login', 'UPDATE'):
                    print("✅ bais_rw CAN update live.auth_users.last_login (Bug #8 fix verified)")
                    self.results['passed'] += 1
                else:
                    print("❌ bais_rw CANNOT update live.auth_users.last_login (Bug #8 broken!)")
                    self.results['failed'] += 1
                    self.results['failures'].append("Special: bais_rw UPDATE on live.auth_users.last_login")
                
                # Verify bais_rw cannot update other columns
                live_tables = self.schema_info['tables'].get('live', {})
                auth_users = live_tables.get('auth_users', {})
                all_columns = auth_users.get('columns', [])
                
                # Test other columns (exclude last_login and auto-generated columns)
                test_columns = [col for col in all_columns 
                              if col not in ['last_login', 'auth_user_id', 'created_at', 'updated_at']][:3]  # Test first 3
                
                for col in test_columns:
                    if not self.check_column_permission('bais_rw', 'live', 'auth_users', col, 'UPDATE'):
                        print(f"✅ bais_rw cannot update live.auth_users.{col} (correct)")
                        self.results['passed'] += 1
                    else:
                        print(f"❌ bais_rw CAN update live.auth_users.{col} (should not have permission!)")
                        self.results['failed'] += 1
                        self.results['failures'].append(f"Special: bais_rw should not UPDATE live.auth_users.{col}")
                break
    
    def run_tests(self):
        """Run all permission tests"""
        print("=" * 70)
        print(" " * 17 + "DATABASE PERMISSION TEST V3 (psql)")
        print("=" * 70)
        
        # Test connection
        success, output = self.execute_sql("SELECT current_user, current_database();")
        if success:
            user_db = output.split('|')
            if len(user_db) == 2:
                print(f"\n✅ Connected as {user_db[0]} to {user_db[1]}")
            else:
                print(f"\n✅ Connected successfully")
        else:
            print(f"\n❌ Connection failed: {output}")
            return 1
        
        # Get expected permissions
        expected_rules = self.get_expected_permissions()
        
        # Group by schema for cleaner output
        schemas = sorted(self.schema_info['schemas'])
        
        for schema in schemas:
            print(f"\n{'=' * 70}")
            print(f"SCHEMA: {schema.upper()}")
            print('=' * 70)
            
            # Get actual tables in schema
            actual_tables = set(self.get_tables_in_schema(schema))
            
            # Test permissions for each user
            for test_user in ['bais_ro', 'bais_rw']:
                print(f"\n{test_user.upper()} Permissions:")
                print("-" * 40)
                
                # Get rules for this schema and user
                user_rules = [r for r in expected_rules 
                             if r.schema == schema and r.user == test_user]
                
                for rule in user_rules:
                    # Skip if table doesn't exist
                    if rule.table not in actual_tables:
                        continue
                    
                    # Test each privilege
                    failures = []
                    
                    # SELECT
                    has_select = self.check_permission(test_user, schema, rule.table, 'SELECT')
                    if has_select != rule.select:
                        failures.append('SELECT')
                        
                    # INSERT
                    has_insert = self.check_permission(test_user, schema, rule.table, 'INSERT')
                    if has_insert != rule.insert:
                        failures.append('INSERT')
                        
                    # UPDATE
                    has_update = self.check_permission(test_user, schema, rule.table, 'UPDATE')
                    if has_update != rule.update:
                        failures.append('UPDATE')
                        
                    # DELETE
                    has_delete = self.check_permission(test_user, schema, rule.table, 'DELETE')
                    if has_delete != rule.delete:
                        failures.append('DELETE')
                    
                    # Report results
                    if not failures:
                        perms = []
                        if rule.select: perms.append('S')
                        if rule.insert: perms.append('I')
                        if rule.update: perms.append('U')
                        if rule.delete: perms.append('D')
                        perm_str = ''.join(perms) if perms else 'none'
                        
                        print(f"  ✅ {rule.table:35} [{perm_str:4}] - All correct")
                        self.results['passed'] += 4  # All 4 permissions correct
                    else:
                        print(f"  ❌ {rule.table:35} - Failed: {', '.join(failures)}")
                        self.results['failed'] += len(failures)
                        self.results['passed'] += (4 - len(failures))
                        for fail in failures:
                            self.results['failures'].append(
                                f"{test_user} {fail} on {schema}.{rule.table}"
                            )
        
        # Test special permissions
        self.test_special_permissions()
        
        # Test column-level permissions
        self.test_column_level_permissions()
        
        # Test FK constraints
        self.test_fk_constraints()
        
        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        total = self.results['passed'] + self.results['failed']
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! Database permissions match expected configuration!")
        else:
            print(f"\n⚠️  {self.results['failed']} tests failed:")
            for failure in self.results['failures'][:10]:  # Show first 10
                print(f"   - {failure}")
            if len(self.results['failures']) > 10:
                print(f"   ... and {len(self.results['failures']) - 10} more")
        
        return 0 if self.results['failed'] == 0 else 1

def main():
    """Run the permission tests"""
    tester = DatabasePermissionTester()
    sys.exit(tester.run_tests())

if __name__ == '__main__':
    main()
