-- =====================================================================
-- BAIS Database Schema Setup Script (v5 - Smart Defaults for Discovery)
-- =====================================================================
-- Purpose: Complete database schema setup executed as rc34924
-- Usage: HOME (after bootstrap) and WORK (database already exists)
--
-- Execute as: rc34924 (BAIS database admin)
-- Database: prutech_bais
--
-- This file uses section markers for Python script extraction:
-- Format: -- ==================== SECTION: NAME ====================
-- =====================================================================

-- ==================== SECTION: USER_CREATION ====================
-- Create the service accounts for the application
-- These users are created by rc34924 using CREATEROLE privilege

-- Create users only if they don't exist (idempotent approach)
-- We don't drop existing users to avoid dependency issues
DO $$
BEGIN
    -- Read-only user for reporting and monitoring
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bais_ro') THEN
        CREATE USER bais_ro WITH PASSWORD 'b7QKJMYmHy0lUM1EhSRbc9H1' LOGIN;
        COMMENT ON ROLE bais_ro IS 'Read-only user for reporting and monitoring';
        RAISE NOTICE 'Created user bais_ro';
    ELSE
        RAISE NOTICE 'User bais_ro already exists, skipping';
    END IF;
    
    -- Read-write user for application business operations
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bais_rw') THEN
        CREATE USER bais_rw WITH PASSWORD 'kpPrIqE4gqG7ILIIb2R5vI0R' LOGIN;
        COMMENT ON ROLE bais_rw IS 'Read-write user for application business data';
        RAISE NOTICE 'Created user bais_rw';
    ELSE
        RAISE NOTICE 'User bais_rw already exists, skipping';
    END IF;
END
$$;

-- ==================== END SECTION: USER_CREATION ====================

-- ==================== SECTION: DATABASE_PREREQUISITES ====================
-- Create shared functions in public schema
-- These are used by triggers across all schemas

-- Create sequence for FQDN placeholder generation
CREATE SEQUENCE IF NOT EXISTS public.host_discovery_seq START WITH 1;
ALTER SEQUENCE public.host_discovery_seq OWNER TO rc34924;
COMMENT ON SEQUENCE public.host_discovery_seq IS 'Sequence for generating unique FQDN placeholders during discovery';

-- Function to automatically update updated timestamps
CREATE OR REPLACE FUNCTION public.update_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

ALTER FUNCTION public.update_updated_column() OWNER TO rc34924;
COMMENT ON FUNCTION public.update_updated_column() IS 'Trigger function to auto-update updated timestamp';

-- ==================== END SECTION: DATABASE_PREREQUISITES ====================

-- ==================== SECTION: SCHEMA:live ====================
-- Production schema with all tables including authentication

-- Drop and recreate schema for clean state
DROP SCHEMA IF EXISTS live CASCADE;
CREATE SCHEMA live AUTHORIZATION rc34924;
COMMENT ON SCHEMA live IS 'Production schema with real data and authentication';

-- Grant schema usage
GRANT ALL ON SCHEMA live TO rc34924;
GRANT USAGE ON SCHEMA live TO bais_ro, bais_rw;

-- Set search path for this section
SET search_path TO live, public;

-- Reference Tables (read-only for applications)
-- =============================================

CREATE TABLE component_types (
    component_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_component_types_name UNIQUE(type_name)
);
ALTER TABLE component_types OWNER TO rc34924;
COMMENT ON TABLE component_types IS 'Reference table for component types';

CREATE TABLE component_abstraction_levels (
    abstraction_level_id SERIAL PRIMARY KEY,
    level_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_abstraction_levels_name UNIQUE(level_name)
);
ALTER TABLE component_abstraction_levels OWNER TO rc34924;
COMMENT ON TABLE component_abstraction_levels IS 'Reference table for component abstraction levels';

CREATE TABLE component_subtypes (
    component_subtype_id SERIAL PRIMARY KEY,
    component_type_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_types(component_type_id),
    subtype_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_subtypes_name_type UNIQUE(component_type_id, subtype_name)
);
ALTER TABLE component_subtypes OWNER TO rc34924;
COMMENT ON TABLE component_subtypes IS 'Reference table for component subtypes';

CREATE TABLE component_ops_statuses (
    ops_status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_operational_statuses_name UNIQUE(status_name)
);
ALTER TABLE component_ops_statuses OWNER TO rc34924;
COMMENT ON TABLE component_ops_statuses IS 'Reference table for operational statuses';

CREATE TABLE component_environments (
    environment_id SERIAL PRIMARY KEY,
    environment_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_environments_name UNIQUE(environment_name)
);
ALTER TABLE component_environments OWNER TO rc34924;
COMMENT ON TABLE component_environments IS 'Reference table for environments';

CREATE TABLE component_physical_locations (
    physical_location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_physical_locations_name UNIQUE(location_name)
);
ALTER TABLE component_physical_locations OWNER TO rc34924;
COMMENT ON TABLE component_physical_locations IS 'Reference table for physical locations';

CREATE TABLE component_relationship_types (
    relationship_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_relationship_types_name UNIQUE(type_name)
);
ALTER TABLE component_relationship_types OWNER TO rc34924;
COMMENT ON TABLE component_relationship_types IS 'Reference table for relationship types between components';

CREATE TABLE component_protocols (
    protocol_id SERIAL PRIMARY KEY,
    protocol_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_protocols_name UNIQUE(protocol_name)
);
ALTER TABLE component_protocols OWNER TO rc34924;
COMMENT ON TABLE component_protocols IS 'Reference table for network protocols';

-- Business Tables
-- ===============

CREATE TABLE biz_components (
    component_id SERIAL PRIMARY KEY,
    -- Unique constraint columns (network identity) come first for clarity
    fqdn VARCHAR(255) NOT NULL DEFAULT (CONCAT('pthost-', LPAD(nextval('public.host_discovery_seq')::text, 3, '0'), '.example.regions.com')),
    app_code VARCHAR(255) NOT NULL DEFAULT '_PT_PENDING_',
    physical_location_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_physical_locations(physical_location_id),
    vlan INTEGER NOT NULL DEFAULT 1 CHECK (vlan >= 1 AND vlan <= 4094),
    ip INET NOT NULL DEFAULT '0.0.0.0',
    port INTEGER NOT NULL DEFAULT 1 CHECK (port >= 1 AND port <= 65535),
    mac MACADDR NOT NULL DEFAULT '00:00:00:00:00:00',
    protocol_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_protocols(protocol_id),
    -- Component classification
    component_type_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_types(component_type_id),
    component_subtype_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_subtypes(component_subtype_id),
    description TEXT DEFAULT '_PT_PENDING_',
    environment_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_environments(environment_id),
    abstraction_level_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_abstraction_levels(abstraction_level_id),
    ops_status_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_ops_statuses(ops_status_id),
    -- Data quality tracking
    record_quality_grade VARCHAR(20) NOT NULL DEFAULT '_PT_YELLOW_RECORD_' CHECK (record_quality_grade IN ('_PT_GREEN_RECORD_', '_PT_YELLOW_RECORD_', '_PT_RED_RECORD_')),
    -- Audit fields
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_components_network_identity UNIQUE(fqdn, physical_location_id, vlan, ip, port, mac)
);
ALTER TABLE biz_components OWNER TO rc34924;
CREATE INDEX idx_components_type ON biz_components(component_type_id);
CREATE INDEX idx_components_subtype ON biz_components(component_subtype_id);
CREATE INDEX idx_components_abstraction ON biz_components(abstraction_level_id);
CREATE INDEX idx_components_status ON biz_components(ops_status_id);
CREATE INDEX idx_components_env ON biz_components(environment_id);
CREATE INDEX idx_components_location ON biz_components(physical_location_id);
COMMENT ON TABLE biz_components IS 'Main table for all system components with network identity';

CREATE TABLE biz_component_relationships (
    relationship_id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES biz_components(component_id) ON DELETE CASCADE,
    related_component_id INTEGER NOT NULL REFERENCES biz_components(component_id) ON DELETE CASCADE,
    relationship_type_id INTEGER NOT NULL REFERENCES component_relationship_types(relationship_type_id),
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_component_relationships UNIQUE(component_id, related_component_id, relationship_type_id),
    CONSTRAINT ck_no_self_relationship CHECK (component_id != related_component_id)
);
ALTER TABLE biz_component_relationships OWNER TO rc34924;
CREATE INDEX idx_component_relationships_component ON biz_component_relationships(component_id);
CREATE INDEX idx_component_relationships_related ON biz_component_relationships(related_component_id);
CREATE INDEX idx_component_relationships_type ON biz_component_relationships(relationship_type_id);
COMMENT ON TABLE biz_component_relationships IS 'Defines relationships between components';

-- Authentication Tables (unique to live schema)
-- ==============================================

CREATE TABLE auth_user_roles (
    auth_user_role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE auth_user_roles OWNER TO rc34924;
COMMENT ON TABLE auth_user_roles IS 'Application user roles (not database roles)';

CREATE TABLE auth_users (
    auth_user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    auth_user_role_id INTEGER NOT NULL REFERENCES auth_user_roles(auth_user_role_id),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Fixed email validation: single backslash for proper regex
    CONSTRAINT ck_users_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
);
ALTER TABLE auth_users OWNER TO rc34924;
CREATE INDEX idx_users_role ON auth_users(auth_user_role_id);
CREATE INDEX idx_users_active ON auth_users(is_active);
COMMENT ON TABLE auth_users IS 'Application users for authentication';

-- Triggers for updated
CREATE TRIGGER update_components_updated BEFORE UPDATE ON biz_components
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_column();

CREATE TRIGGER update_component_relationships_updated BEFORE UPDATE ON biz_component_relationships
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON auth_users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_column();

-- Insert Reference Data
-- =====================

INSERT INTO component_types (component_type_id, type_name, description, created_by) VALUES
    (1, 'application', 'Core software delivering business logic and functionality', 'schema_init_script'),
    (2, 'polyglot_persistence', 'Diverse data technologies chosen for specific patterns', 'schema_init_script'),
    (3, 'block_level_persistence', 'Raw shared storage infrastructure capacity', 'schema_init_script'),
    (4, 'networking', 'Communication fabric for traffic distribution and routing', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_abstraction_levels (abstraction_level_id, level_name, description, created_by) VALUES
    (1, 'physical_bare_metal', 'Component hosted on physical hardware', 'schema_init_script'),
    (2, 'virtual_machine', 'Component hosted within a guest VM', 'schema_init_script'),
    (3, 'container', 'Containerized Component hosted in isolated user-space instance', 'schema_init_script'),
    (4, 'container_in_vm', 'Containerized Componennt hosted within a guest VM', 'schema_init_script'),
    (5, 'k8s_pod', 'Component hosted within a Kubernetes Pod', 'schema_init_script'),
    (6, 'container_in_k8s_pod', 'Containerized Component hosted within a Kubernetes Pod', 'schema_init_script'),
    (7, 'managed_service', 'Consumed as service with no infrastructure managed by user', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

-- Insert subtypes with explicit IDs
INSERT INTO component_subtypes (component_subtype_id, component_type_id, subtype_name, description, created_by) VALUES
    -- Application subtypes (type_id = 1)
    (1, 1, 'web_application', 'Browser-based application', 'schema_init_script'),
    (2, 1, 'api_service', 'RESTful or GraphQL API', 'schema_init_script'),
    (3, 1, 'microservice', 'Small, focused service', 'schema_init_script'),
    (4, 1, 'batch_job', 'Scheduled processing job', 'schema_init_script'),
    -- Polyglot persistence subtypes (type_id = 2)
    (5, 2, 'relational_database', 'RDBMS like PostgreSQL, MySQL', 'schema_init_script'),
    (6, 2, 'nosql_database', 'Document, key-value, or graph database', 'schema_init_script'),
    (7, 2, 'message_queue', 'Message broker or streaming platform', 'schema_init_script'),
    (8, 2, 'cache', 'In-memory data store', 'schema_init_script'),
    -- Block level persistence subtypes (type_id = 3)
    (9, 3, 'storage_area_network', 'SAN storage', 'schema_init_script'),
    (10, 3, 'network_attached_storage', 'NAS storage', 'schema_init_script'),
    (11, 3, 'object_storage', 'Cloud object storage', 'schema_init_script'),
    -- Networking subtypes (type_id = 4)
    (12, 4, 'load_balancer', 'Traffic distribution', 'schema_init_script'),
    (13, 4, 'api_gateway', 'API management and routing', 'schema_init_script'),
    (14, 4, 'firewall', 'Network security', 'schema_init_script'),
    (15, 4, 'switch', 'Network switching', 'schema_init_script'),
    -- Special placeholder subtypes (belong to their respective placeholder types)
    (999, 999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, 998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_ops_statuses (ops_status_id, status_name, description, created_by) VALUES
    (1, 'OPERATIONAL', 'Active service in optimal state', 'schema_init_script'),
    (2, 'DEGRADED', 'Active service in degraded state', 'schema_init_script'),
    (3, 'MAINTENANCE', 'Active service in maintenance mode', 'schema_init_script'),
    (4, 'RETIRED', 'Inactive service with infrastructure still in place', 'schema_init_script'),
    (5, 'DECOMMISSIONED', 'Inactive service with infrastructure permanently removed', 'schema_init_script'),
    (6, 'PLANNED', 'Inactive service in strategic development phase', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_environments (environment_id, environment_name, description, created_by) VALUES
    (1, 'DEV', 'Development environment', 'schema_init_script'),
    (2, 'TEST', 'Testing environment', 'schema_init_script'),
    (3, 'STAGING', 'Staging environment', 'schema_init_script'),
    (4, 'PROD', 'Production environment', 'schema_init_script'),
    (5, 'UAT', 'User Acceptance Testing environment', 'schema_init_script'),
    (6, 'QA', 'Quality Assurance environment', 'schema_init_script'),
    (7, 'DR', 'Disaster Recovery environment', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_physical_locations (physical_location_id, location_name, description, created_by) VALUES
    (1, 'DC01_AL', 'Alabama Datacenter', 'schema_init_script'),
    (2, 'DC02_NC', 'North Carolina Datacenter', 'schema_init_script'),
    (3, 'DC03_VA', 'Virginia Datacenter', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_relationship_types (relationship_type_id, type_name, description, created_by) VALUES
    (1, 'replicates_from', 'Component replicates data from another component. Use cases: Primary/Replica Databases | Master/Slave Apps', 'schema_init_script'),
    (2, 'fails_over_to', 'Component fails over to another component. Use cases: Standby relationships | Disaster recovery', 'schema_init_script'),
    (3, 'consumes_api_from', 'Component consumes API services from another component. Use cases: Microservice dependencies | Service mesh', 'schema_init_script'),
    (4, 'persists_to', 'Component persists data to another component. Use cases: App to database | App to object storage', 'schema_init_script'),
    (5, 'publishes_to', 'Component publishes messages to another component. Use cases: App to Kafka | App to message queue', 'schema_init_script'),
    (6, 'subscribes_to', 'Component subscribes to messages from another component. Use cases: App from event streams | App from notifications', 'schema_init_script'),
    (7, 'proxied_by', 'Component traffic is proxied by another component. Use cases: App from load balancer | App from API gateway', 'schema_init_script'),
    (8, 'authenticates_via', 'Component authenticates through another component. Use cases: Apps to identity providers | SSO relationships', 'schema_init_script'),
    (9, 'monitors', 'Component monitors another component. Use cases: Monitoring tools to infrastructure', 'schema_init_script'),
    (10, 'collaborates_with', 'Component collaborates with another component to deliver composite business functionality. Use cases: Distributed feature implementation | Multi-service workflows', 'schema_init_script'),
    (11, 'peers_with', 'Component operates as a peer with another component at the same architectural level. Use cases: Clustered applications | Load-balanced instances', 'schema_init_script'),
    (12, 'vm_guest_of', 'Component is a virtual machine guest of another component. Use cases: VM to hypervisor host', 'schema_init_script'),
    (13, 'load_balanced_by', 'Component traffic is load balanced by another component. Use cases: App servers behind load balancer', 'schema_init_script'),
    (14, 'communicates_with', 'Component has general communication with another component. Use cases: Generic network communication', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_protocols (protocol_id, protocol_name, description, created_by) VALUES
    (1, 'HTTP', 'Hypertext Transfer Protocol', 'schema_init_script'),
    (2, 'HTTPS', 'HTTP Secure', 'schema_init_script'),
    (3, 'TCP', 'Transmission Control Protocol', 'schema_init_script'),
    (4, 'UDP', 'User Datagram Protocol', 'schema_init_script'),
    (5, 'FTP', 'File Transfer Protocol', 'schema_init_script'),
    (6, 'FTPS', 'FTP Secure', 'schema_init_script'),
    (7, 'SFTP', 'SSH File Transfer Protocol', 'schema_init_script'),
    (8, 'SSH', 'Secure Shell', 'schema_init_script'),
    (9, 'Telnet', 'Telnet Protocol', 'schema_init_script'),
    (10, 'SMTP', 'Simple Mail Transfer Protocol', 'schema_init_script'),
    (11, 'SMTPS', 'SMTP Secure', 'schema_init_script'),
    (12, 'POP3', 'Post Office Protocol v3', 'schema_init_script'),
    (13, 'IMAP', 'Internet Message Access Protocol', 'schema_init_script'),
    (14, 'DNS', 'Domain Name System', 'schema_init_script'),
    (15, 'NTP', 'Network Time Protocol', 'schema_init_script'),
    (16, 'SNMP', 'Simple Network Management Protocol', 'schema_init_script'),
    (17, 'MySQL', 'MySQL Protocol', 'schema_init_script'),
    (18, 'PostgreSQL', 'PostgreSQL Protocol', 'schema_init_script'),
    (19, 'MSSQL', 'Microsoft SQL Server Protocol', 'schema_init_script'),
    (20, 'Oracle', 'Oracle Database Protocol', 'schema_init_script'),
    (21, 'SMB', 'Server Message Block', 'schema_init_script'),
    (22, 'NFS', 'Network File System', 'schema_init_script'),
    (23, 'RDP', 'Remote Desktop Protocol', 'schema_init_script'),
    (24, 'VNC', 'Virtual Network Computing', 'schema_init_script'),
    (25, 'TN3270', 'Telnet 3270', 'schema_init_script'),
    (26, 'TN5250', 'Telnet 5250', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO auth_user_roles (role_name, description) VALUES
    ('admin', 'Full system administrator access'),
    ('developer', 'Developer access - read/write for non-production'),
    ('analyst', 'Business analyst - read-only access'),
    ('viewer', 'Basic read-only access');

-- Grant permissions for live schema
-- ==================================

-- Read-only user (bais_ro)
GRANT SELECT ON ALL TABLES IN SCHEMA live TO bais_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA live TO bais_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA live 
    GRANT SELECT ON TABLES TO bais_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA live 
    GRANT SELECT ON SEQUENCES TO bais_ro;

-- Read-write user (bais_rw)
-- Reference tables: SELECT only
GRANT SELECT ON live.component_types TO bais_rw;
GRANT SELECT ON live.component_abstraction_levels TO bais_rw;
GRANT SELECT ON live.component_subtypes TO bais_rw;
GRANT SELECT ON live.component_ops_statuses TO bais_rw;
GRANT SELECT ON live.component_environments TO bais_rw;
GRANT SELECT ON live.component_physical_locations TO bais_rw;
GRANT SELECT ON live.component_relationship_types TO bais_rw;
GRANT SELECT ON live.component_protocols TO bais_rw;

-- Business tables: Full CRUD
GRANT SELECT, INSERT, UPDATE, DELETE ON live.biz_components TO bais_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON live.biz_component_relationships TO bais_rw;

-- Auth tables: Special permissions
GRANT SELECT ON live.auth_user_roles TO bais_rw;
GRANT SELECT ON live.auth_users TO bais_rw;
-- CRITICAL FIX for Bug #8: Allow updating last_login for authentication
GRANT UPDATE (last_login) ON live.auth_users TO bais_rw;

-- Grant sequence usage for inserts
GRANT USAGE ON ALL SEQUENCES IN SCHEMA live TO bais_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA live 
    GRANT USAGE ON SEQUENCES TO bais_rw;

-- ==================== END SECTION: SCHEMA:live ====================

-- ==================== SECTION: SCHEMA:live_masked ====================
-- Production schema with masked sensitive data (no auth tables)

-- Drop and recreate schema for clean state
DROP SCHEMA IF EXISTS live_masked CASCADE;
CREATE SCHEMA live_masked AUTHORIZATION rc34924;
COMMENT ON SCHEMA live_masked IS 'Production schema with masked sensitive information';

-- Grant schema usage
GRANT ALL ON SCHEMA live_masked TO rc34924;
GRANT USAGE ON SCHEMA live_masked TO bais_ro, bais_rw;

-- Set search path for this section
SET search_path TO live_masked, public;

-- Reference Tables (identical structure to live)
-- ===============================================

CREATE TABLE component_types (
    component_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_component_types_name UNIQUE(type_name)
);
ALTER TABLE component_types OWNER TO rc34924;

CREATE TABLE component_abstraction_levels (
    abstraction_level_id SERIAL PRIMARY KEY,
    level_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_abstraction_levels_name UNIQUE(level_name)
);
ALTER TABLE component_abstraction_levels OWNER TO rc34924;

CREATE TABLE component_subtypes (
    component_subtype_id SERIAL PRIMARY KEY,
    component_type_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_types(component_type_id),
    subtype_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_subtypes_name_type UNIQUE(component_type_id, subtype_name)
);
ALTER TABLE component_subtypes OWNER TO rc34924;

CREATE TABLE component_ops_statuses (
    ops_status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_operational_statuses_name UNIQUE(status_name)
);
ALTER TABLE component_ops_statuses OWNER TO rc34924;

CREATE TABLE component_environments (
    environment_id SERIAL PRIMARY KEY,
    environment_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_environments_name UNIQUE(environment_name)
);
ALTER TABLE component_environments OWNER TO rc34924;

CREATE TABLE component_physical_locations (
    physical_location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_physical_locations_name UNIQUE(location_name)
);
ALTER TABLE component_physical_locations OWNER TO rc34924;

CREATE TABLE component_relationship_types (
    relationship_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_relationship_types_name UNIQUE(type_name)
);
ALTER TABLE component_relationship_types OWNER TO rc34924;

CREATE TABLE component_protocols (
    protocol_id SERIAL PRIMARY KEY,
    protocol_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_protocols_name UNIQUE(protocol_name)
);
ALTER TABLE component_protocols OWNER TO rc34924;

-- Business Tables with masked sensitive data
CREATE TABLE biz_components (
    component_id SERIAL PRIMARY KEY,
    -- Unique constraint columns (network identity) come first for clarity
    fqdn VARCHAR(255) NOT NULL DEFAULT (CONCAT('pthost-', LPAD(nextval('public.host_discovery_seq')::text, 3, '0'), '.example.regions.com')),
    app_code VARCHAR(255) NOT NULL DEFAULT '_PT_PENDING_',
    physical_location_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_physical_locations(physical_location_id),
    vlan INTEGER NOT NULL DEFAULT 1 CHECK (vlan >= 1 AND vlan <= 4094),
    ip INET NOT NULL DEFAULT '0.0.0.0',
    port INTEGER NOT NULL DEFAULT 1 CHECK (port >= 1 AND port <= 65535),
    mac MACADDR NOT NULL DEFAULT '00:00:00:00:00:00',
    protocol_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_protocols(protocol_id),
    -- Component classification
    component_type_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_types(component_type_id),
    component_subtype_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_subtypes(component_subtype_id),
    description TEXT DEFAULT '_PT_PENDING_',
    environment_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_environments(environment_id),
    abstraction_level_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_abstraction_levels(abstraction_level_id),
    ops_status_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_ops_statuses(ops_status_id),
    -- Data quality tracking
    record_quality_grade VARCHAR(20) NOT NULL DEFAULT '_PT_YELLOW_RECORD_' CHECK (record_quality_grade IN ('_PT_GREEN_RECORD_', '_PT_YELLOW_RECORD_', '_PT_RED_RECORD_')),
    -- Audit fields
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_components_network_identity UNIQUE(fqdn, physical_location_id, vlan, ip, port, mac)
);
ALTER TABLE biz_components OWNER TO rc34924;
CREATE INDEX idx_components_type ON biz_components(component_type_id);
CREATE INDEX idx_components_subtype ON biz_components(component_subtype_id);
CREATE INDEX idx_components_abstraction ON biz_components(abstraction_level_id);
CREATE INDEX idx_components_status ON biz_components(ops_status_id);
CREATE INDEX idx_components_env ON biz_components(environment_id);
CREATE INDEX idx_components_location ON biz_components(physical_location_id);

CREATE TABLE biz_component_relationships (
    relationship_id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES biz_components(component_id) ON DELETE CASCADE,
    related_component_id INTEGER NOT NULL REFERENCES biz_components(component_id) ON DELETE CASCADE,
    relationship_type_id INTEGER NOT NULL REFERENCES component_relationship_types(relationship_type_id),
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_component_relationships UNIQUE(component_id, related_component_id, relationship_type_id),
    CONSTRAINT ck_no_self_relationship CHECK (component_id != related_component_id)
);
ALTER TABLE biz_component_relationships OWNER TO rc34924;
CREATE INDEX idx_component_relationships_component ON biz_component_relationships(component_id);
CREATE INDEX idx_component_relationships_related ON biz_component_relationships(related_component_id);
CREATE INDEX idx_component_relationships_type ON biz_component_relationships(relationship_type_id);

-- Triggers
CREATE TRIGGER update_components_updated BEFORE UPDATE ON biz_components
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_column();

CREATE TRIGGER update_component_relationships_updated BEFORE UPDATE ON biz_component_relationships
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_column();

-- Insert Reference Data (same as live)
INSERT INTO component_types (component_type_id, type_name, description, created_by) VALUES
    (1, 'application', 'Core software delivering business logic and functionality', 'schema_init_script'),
    (2, 'polyglot_persistence', 'Diverse data technologies chosen for specific patterns', 'schema_init_script'),
    (3, 'block_level_persistence', 'Raw shared storage infrastructure capacity', 'schema_init_script'),
    (4, 'networking', 'Communication fabric for traffic distribution and routing', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_abstraction_levels (abstraction_level_id, level_name, description, created_by) VALUES
    (1, 'physical_bare_metal', 'Component hosted on physical hardware', 'schema_init_script'),
    (2, 'virtual_machine', 'Component hosted within a guest VM', 'schema_init_script'),
    (3, 'container', 'Containerized Component hosted in isolated user-space instance', 'schema_init_script'),
    (4, 'container_in_vm', 'Containerized Componennt hosted within a guest VM', 'schema_init_script'),
    (5, 'k8s_pod', 'Component hosted within a Kubernetes Pod', 'schema_init_script'),
    (6, 'container_in_k8s_pod', 'Containerized Component hosted within a Kubernetes Pod', 'schema_init_script'),
    (7, 'managed_service', 'Consumed as service with no infrastructure managed by user', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

-- Insert subtypes with explicit IDs
INSERT INTO component_subtypes (component_subtype_id, component_type_id, subtype_name, description, created_by) VALUES
    -- Application subtypes (type_id = 1)
    (1, 1, 'web_application', 'Browser-based application', 'schema_init_script'),
    (2, 1, 'api_service', 'RESTful or GraphQL API', 'schema_init_script'),
    (3, 1, 'microservice', 'Small, focused service', 'schema_init_script'),
    (4, 1, 'batch_job', 'Scheduled processing job', 'schema_init_script'),
    -- Polyglot persistence subtypes (type_id = 2)
    (5, 2, 'relational_database', 'RDBMS like PostgreSQL, MySQL', 'schema_init_script'),
    (6, 2, 'nosql_database', 'Document, key-value, or graph database', 'schema_init_script'),
    (7, 2, 'message_queue', 'Message broker or streaming platform', 'schema_init_script'),
    (8, 2, 'cache', 'In-memory data store', 'schema_init_script'),
    -- Block level persistence subtypes (type_id = 3)
    (9, 3, 'storage_area_network', 'SAN storage', 'schema_init_script'),
    (10, 3, 'network_attached_storage', 'NAS storage', 'schema_init_script'),
    (11, 3, 'object_storage', 'Cloud object storage', 'schema_init_script'),
    -- Networking subtypes (type_id = 4)
    (12, 4, 'load_balancer', 'Traffic distribution', 'schema_init_script'),
    (13, 4, 'api_gateway', 'API management and routing', 'schema_init_script'),
    (14, 4, 'firewall', 'Network security', 'schema_init_script'),
    (15, 4, 'switch', 'Network switching', 'schema_init_script'),
    -- Special placeholder subtypes (belong to their respective placeholder types)
    (999, 999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, 998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_ops_statuses (ops_status_id, status_name, description, created_by) VALUES
    (1, 'OPERATIONAL', 'Active service in optimal state', 'schema_init_script'),
    (2, 'DEGRADED', 'Active service in degraded state', 'schema_init_script'),
    (3, 'MAINTENANCE', 'Active service in maintenance mode', 'schema_init_script'),
    (4, 'RETIRED', 'Inactive service with infrastructure still in place', 'schema_init_script'),
    (5, 'DECOMMISSIONED', 'Inactive service with infrastructure permanently removed', 'schema_init_script'),
    (6, 'PLANNED', 'Inactive service in strategic development phase', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_environments (environment_id, environment_name, description, created_by) VALUES
    (1, 'DEV', 'Development environment', 'schema_init_script'),
    (2, 'TEST', 'Testing environment', 'schema_init_script'),
    (3, 'STAGING', 'Staging environment', 'schema_init_script'),
    (4, 'PROD', 'Production environment', 'schema_init_script'),
    (5, 'UAT', 'User Acceptance Testing environment', 'schema_init_script'),
    (6, 'QA', 'Quality Assurance environment', 'schema_init_script'),
    (7, 'DR', 'Disaster Recovery environment', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_physical_locations (physical_location_id, location_name, description, created_by) VALUES
    (1, 'DC01_AL', 'Alabama Datacenter', 'schema_init_script'),
    (2, 'DC02_NC', 'North Carolina Datacenter', 'schema_init_script'),
    (3, 'DC03_VA', 'Virginia Datacenter', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_relationship_types (relationship_type_id, type_name, description, created_by) VALUES
    (1, 'replicates_from', 'Component replicates data from another component. Use cases: Primary/Replica Databases | Master/Slave Apps', 'schema_init_script'),
    (2, 'fails_over_to', 'Component fails over to another component. Use cases: Standby relationships | Disaster recovery', 'schema_init_script'),
    (3, 'consumes_api_from', 'Component consumes API services from another component. Use cases: Microservice dependencies | Service mesh', 'schema_init_script'),
    (4, 'persists_to', 'Component persists data to another component. Use cases: App to database | App to object storage', 'schema_init_script'),
    (5, 'publishes_to', 'Component publishes messages to another component. Use cases: App to Kafka | App to message queue', 'schema_init_script'),
    (6, 'subscribes_to', 'Component subscribes to messages from another component. Use cases: App from event streams | App from notifications', 'schema_init_script'),
    (7, 'proxied_by', 'Component traffic is proxied by another component. Use cases: App from load balancer | App from API gateway', 'schema_init_script'),
    (8, 'authenticates_via', 'Component authenticates through another component. Use cases: Apps to identity providers | SSO relationships', 'schema_init_script'),
    (9, 'monitors', 'Component monitors another component. Use cases: Monitoring tools to infrastructure', 'schema_init_script'),
    (10, 'collaborates_with', 'Component collaborates with another component to deliver composite business functionality. Use cases: Distributed feature implementation | Multi-service workflows', 'schema_init_script'),
    (11, 'peers_with', 'Component operates as a peer with another component at the same architectural level. Use cases: Clustered applications | Load-balanced instances', 'schema_init_script'),
    (12, 'vm_guest_of', 'Component is a virtual machine guest of another component. Use cases: VM to hypervisor host', 'schema_init_script'),
    (13, 'load_balanced_by', 'Component traffic is load balanced by another component. Use cases: App servers behind load balancer', 'schema_init_script'),
    (14, 'communicates_with', 'Component has general communication with another component. Use cases: Generic network communication', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

INSERT INTO component_protocols (protocol_id, protocol_name, description, created_by) VALUES
    (1, 'HTTP', 'Hypertext Transfer Protocol', 'schema_init_script'),
    (2, 'HTTPS', 'HTTP Secure', 'schema_init_script'),
    (3, 'TCP', 'Transmission Control Protocol', 'schema_init_script'),
    (4, 'UDP', 'User Datagram Protocol', 'schema_init_script'),
    (5, 'FTP', 'File Transfer Protocol', 'schema_init_script'),
    (6, 'FTPS', 'FTP Secure', 'schema_init_script'),
    (7, 'SFTP', 'SSH File Transfer Protocol', 'schema_init_script'),
    (8, 'SSH', 'Secure Shell', 'schema_init_script'),
    (9, 'Telnet', 'Telnet Protocol', 'schema_init_script'),
    (10, 'SMTP', 'Simple Mail Transfer Protocol', 'schema_init_script'),
    (11, 'SMTPS', 'SMTP Secure', 'schema_init_script'),
    (12, 'POP3', 'Post Office Protocol v3', 'schema_init_script'),
    (13, 'IMAP', 'Internet Message Access Protocol', 'schema_init_script'),
    (14, 'DNS', 'Domain Name System', 'schema_init_script'),
    (15, 'NTP', 'Network Time Protocol', 'schema_init_script'),
    (16, 'SNMP', 'Simple Network Management Protocol', 'schema_init_script'),
    (17, 'MySQL', 'MySQL Protocol', 'schema_init_script'),
    (18, 'PostgreSQL', 'PostgreSQL Protocol', 'schema_init_script'),
    (19, 'MSSQL', 'Microsoft SQL Server Protocol', 'schema_init_script'),
    (20, 'Oracle', 'Oracle Database Protocol', 'schema_init_script'),
    (21, 'SMB', 'Server Message Block', 'schema_init_script'),
    (22, 'NFS', 'Network File System', 'schema_init_script'),
    (23, 'RDP', 'Remote Desktop Protocol', 'schema_init_script'),
    (24, 'VNC', 'Virtual Network Computing', 'schema_init_script'),
    (25, 'TN3270', 'Telnet 3270', 'schema_init_script'),
    (26, 'TN5250', 'Telnet 5250', 'schema_init_script'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'schema_init_script'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'schema_init_script');

-- Grant permissions for live_masked schema
-- =========================================

-- Read-only user (bais_ro)
GRANT SELECT ON ALL TABLES IN SCHEMA live_masked TO bais_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA live_masked TO bais_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA live_masked 
    GRANT SELECT ON TABLES TO bais_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA live_masked 
    GRANT SELECT ON SEQUENCES TO bais_ro;

-- Read-write user (bais_rw)
-- Reference tables: SELECT only
GRANT SELECT ON live_masked.component_types TO bais_rw;
GRANT SELECT ON live_masked.component_abstraction_levels TO bais_rw;
GRANT SELECT ON live_masked.component_subtypes TO bais_rw;
GRANT SELECT ON live_masked.component_ops_statuses TO bais_rw;
GRANT SELECT ON live_masked.component_environments TO bais_rw;
GRANT SELECT ON live_masked.component_physical_locations TO bais_rw;
GRANT SELECT ON live_masked.component_relationship_types TO bais_rw;
GRANT SELECT ON live_masked.component_protocols TO bais_rw;

-- Business tables: Full CRUD
GRANT SELECT, INSERT, UPDATE, DELETE ON live_masked.biz_components TO bais_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON live_masked.biz_component_relationships TO bais_rw;

-- Grant sequence usage
GRANT USAGE ON ALL SEQUENCES IN SCHEMA live_masked TO bais_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA live_masked 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bais_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA live_masked 
    GRANT USAGE ON SEQUENCES TO bais_rw;

-- ==================== END SECTION: SCHEMA:live_masked ====================

-- ==================== SECTION: SCHEMA:demo ====================
-- Demo schema with sample data (no auth tables)

-- Drop and recreate schema for clean state
DROP SCHEMA IF EXISTS demo CASCADE;
CREATE SCHEMA demo AUTHORIZATION rc34924;
COMMENT ON SCHEMA demo IS 'Demonstration schema with sample data';

-- Grant schema usage
GRANT ALL ON SCHEMA demo TO rc34924;
GRANT USAGE ON SCHEMA demo TO bais_ro, bais_rw;

-- Set search path for this section
SET search_path TO demo, public;

-- Reference Tables (identical structure)
-- =======================================

CREATE TABLE component_types (
    component_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_component_types_name UNIQUE(type_name)
);
ALTER TABLE component_types OWNER TO rc34924;

CREATE TABLE component_abstraction_levels (
    abstraction_level_id SERIAL PRIMARY KEY,
    level_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_abstraction_levels_name UNIQUE(level_name)
);
ALTER TABLE component_abstraction_levels OWNER TO rc34924;

CREATE TABLE component_subtypes (
    component_subtype_id SERIAL PRIMARY KEY,
    component_type_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_types(component_type_id),
    subtype_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_subtypes_name_type UNIQUE(component_type_id, subtype_name)
);
ALTER TABLE component_subtypes OWNER TO rc34924;

CREATE TABLE component_ops_statuses (
    ops_status_id SERIAL PRIMARY KEY,
    status_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_operational_statuses_name UNIQUE(status_name)
);
ALTER TABLE component_ops_statuses OWNER TO rc34924;

CREATE TABLE component_environments (
    environment_id SERIAL PRIMARY KEY,
    environment_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_environments_name UNIQUE(environment_name)
);
ALTER TABLE component_environments OWNER TO rc34924;

CREATE TABLE component_physical_locations (
    physical_location_id SERIAL PRIMARY KEY,
    location_name VARCHAR(100) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_physical_locations_name UNIQUE(location_name)
);
ALTER TABLE component_physical_locations OWNER TO rc34924;

CREATE TABLE component_relationship_types (
    relationship_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_relationship_types_name UNIQUE(type_name)
);
ALTER TABLE component_relationship_types OWNER TO rc34924;

CREATE TABLE component_protocols (
    protocol_id SERIAL PRIMARY KEY,
    protocol_name VARCHAR(30) NOT NULL,
    description TEXT DEFAULT '_PT_PENDING_',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_protocols_name UNIQUE(protocol_name)
);
ALTER TABLE component_protocols OWNER TO rc34924;

-- Business Tables
CREATE TABLE biz_components (
    component_id SERIAL PRIMARY KEY,
    -- Unique constraint columns (network identity) come first for clarity
    fqdn VARCHAR(255) NOT NULL DEFAULT (CONCAT('pthost-', LPAD(nextval('public.host_discovery_seq')::text, 3, '0'), '.example.regions.com')),
    app_code VARCHAR(255) NOT NULL DEFAULT '_PT_PENDING_',
    physical_location_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_physical_locations(physical_location_id),
    vlan INTEGER NOT NULL DEFAULT 1 CHECK (vlan >= 1 AND vlan <= 4094),
    ip INET NOT NULL DEFAULT '0.0.0.0',
    port INTEGER NOT NULL DEFAULT 1 CHECK (port >= 1 AND port <= 65535),
    mac MACADDR NOT NULL DEFAULT '00:00:00:00:00:00',
    protocol_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_protocols(protocol_id),
    -- Component classification
    component_type_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_types(component_type_id),
    component_subtype_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_subtypes(component_subtype_id),
    description TEXT DEFAULT '_PT_PENDING_',
    environment_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_environments(environment_id),
    abstraction_level_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_abstraction_levels(abstraction_level_id),
    ops_status_id INTEGER NOT NULL DEFAULT 999 REFERENCES component_ops_statuses(ops_status_id),
    -- Data quality tracking
    record_quality_grade VARCHAR(20) NOT NULL DEFAULT '_PT_YELLOW_RECORD_' CHECK (record_quality_grade IN ('_PT_GREEN_RECORD_', '_PT_YELLOW_RECORD_', '_PT_RED_RECORD_')),
    -- Audit fields
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_components_network_identity UNIQUE(fqdn, physical_location_id, vlan, ip, port, mac)
);
ALTER TABLE biz_components OWNER TO rc34924;
CREATE INDEX idx_components_type ON biz_components(component_type_id);
CREATE INDEX idx_components_subtype ON biz_components(component_subtype_id);
CREATE INDEX idx_components_abstraction ON biz_components(abstraction_level_id);
CREATE INDEX idx_components_status ON biz_components(ops_status_id);
CREATE INDEX idx_components_env ON biz_components(environment_id);
CREATE INDEX idx_components_location ON biz_components(physical_location_id);

CREATE TABLE biz_component_relationships (
    relationship_id SERIAL PRIMARY KEY,
    component_id INTEGER NOT NULL REFERENCES biz_components(component_id) ON DELETE CASCADE,
    related_component_id INTEGER NOT NULL REFERENCES biz_components(component_id) ON DELETE CASCADE,
    relationship_type_id INTEGER NOT NULL REFERENCES component_relationship_types(relationship_type_id),
    description VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255) NOT NULL,
    CONSTRAINT uk_component_relationships UNIQUE(component_id, related_component_id, relationship_type_id),
    CONSTRAINT ck_no_self_relationship CHECK (component_id != related_component_id)
);
ALTER TABLE biz_component_relationships OWNER TO rc34924;
CREATE INDEX idx_component_relationships_component ON biz_component_relationships(component_id);
CREATE INDEX idx_component_relationships_related ON biz_component_relationships(related_component_id);
CREATE INDEX idx_component_relationships_type ON biz_component_relationships(relationship_type_id);

-- Triggers
CREATE TRIGGER update_components_updated BEFORE UPDATE ON biz_components
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_column();

CREATE TRIGGER update_component_relationships_updated BEFORE UPDATE ON biz_component_relationships
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_column();

-- Insert Reference Data
INSERT INTO component_types (component_type_id, type_name, description, created_by) VALUES
    (1, 'application', 'Core software delivering business logic and functionality', 'demo'),
    (2, 'polyglot_persistence', 'Diverse data technologies chosen for specific patterns', 'demo'),
    (3, 'block_level_persistence', 'Raw shared storage infrastructure capacity', 'demo'),
    (4, 'networking', 'Communication fabric for traffic distribution and routing', 'demo'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

INSERT INTO component_abstraction_levels (abstraction_level_id, level_name, description, created_by) VALUES
    (1, 'physical_bare_metal', 'Component hosted on physical hardware', 'demo'),
    (2, 'virtual_machine', 'Component hosted within a guest VM', 'demo'),
    (3, 'container', 'Containerized Component hosted in isolated user-space instance', 'demo'),
    (4, 'container_in_vm', 'Containerized Componennt hosted within a guest VM', 'demo'),
    (5, 'k8s_pod', 'Component hosted within a Kubernetes Pod', 'demo'),
    (6, 'container_in_k8s_pod', 'Containerized Component hosted within a Kubernetes Pod', 'demo'),
    (7, 'managed_service', 'Consumed as service with no infrastructure managed by user', 'demo'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

-- Insert subtypes with explicit IDs
INSERT INTO component_subtypes (component_subtype_id, component_type_id, subtype_name, description, created_by) VALUES
    -- Application subtypes (type_id = 1)
    (1, 1, 'web_application', 'Browser-based application', 'demo'),
    (2, 1, 'api_service', 'RESTful or GraphQL API', 'demo'),
    (3, 1, 'microservice', 'Small, focused service', 'demo'),
    (4, 1, 'batch_job', 'Scheduled processing job', 'demo'),
    -- Polyglot persistence subtypes (type_id = 2)
    (5, 2, 'relational_database', 'RDBMS like PostgreSQL, MySQL', 'demo'),
    (6, 2, 'nosql_database', 'Document, key-value, or graph database', 'demo'),
    (7, 2, 'message_queue', 'Message broker or streaming platform', 'demo'),
    (8, 2, 'cache', 'In-memory data store', 'demo'),
    -- Block level persistence subtypes (type_id = 3)
    (9, 3, 'storage_area_network', 'SAN storage', 'demo'),
    (10, 3, 'network_attached_storage', 'NAS storage', 'demo'),
    (11, 3, 'object_storage', 'Cloud object storage', 'demo'),
    -- Networking subtypes (type_id = 4)
    (12, 4, 'load_balancer', 'Traffic distribution', 'demo'),
    (13, 4, 'api_gateway', 'API management and routing', 'demo'),
    (14, 4, 'firewall', 'Network security', 'demo'),
    (15, 4, 'switch', 'Network switching', 'demo'),
    -- Special placeholder subtypes (belong to their respective placeholder types)
    (999, 999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, 998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

INSERT INTO component_ops_statuses (ops_status_id, status_name, description, created_by) VALUES
    (1, 'OPERATIONAL', 'Active service in optimal state', 'demo'),
    (2, 'DEGRADED', 'Active service in degraded state', 'demo'),
    (3, 'MAINTENANCE', 'Active service in maintenance mode', 'demo'),
    (4, 'RETIRED', 'Inactive service with infrastructure still in place', 'demo'),
    (5, 'DECOMMISSIONED', 'Inactive service with infrastructure permanently removed', 'demo'),
    (6, 'PLANNED', 'Inactive service in strategic development phase', 'demo'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

INSERT INTO component_environments (environment_id, environment_name, description, created_by) VALUES
    (1, 'DEV', 'Development environment', 'demo'),
    (2, 'TEST', 'Testing environment', 'demo'),
    (3, 'STAGING', 'Staging environment', 'demo'),
    (4, 'PROD', 'Production environment', 'demo'),
    (5, 'UAT', 'User Acceptance Testing environment', 'demo'),
    (6, 'QA', 'Quality Assurance environment', 'demo'),
    (7, 'DR', 'Disaster Recovery environment', 'demo'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

INSERT INTO component_physical_locations (physical_location_id, location_name, description, created_by) VALUES
    (1, 'DC01_AL', 'Alabama Datacenter', 'demo'),
    (2, 'DC02_NC', 'North Carolina Datacenter', 'demo'),
    (3, 'DC03_VA', 'Virginia Datacenter', 'demo'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

INSERT INTO component_relationship_types (relationship_type_id, type_name, description, created_by) VALUES
    (1, 'replicates_from', 'Component replicates data from another component. Use cases: Primary/Replica Databases | Master/Slave Apps', 'demo'),
    (2, 'fails_over_to', 'Component fails over to another component. Use cases: Standby relationships | Disaster recovery', 'demo'),
    (3, 'consumes_api_from', 'Component consumes API services from another component. Use cases: Microservice dependencies | Service mesh', 'demo'),
    (4, 'persists_to', 'Component persists data to another component. Use cases: App to database | App to object storage', 'demo'),
    (5, 'publishes_to', 'Component publishes messages to another component. Use cases: App to Kafka | App to message queue', 'demo'),
    (6, 'subscribes_to', 'Component subscribes to messages from another component. Use cases: App from event streams | App from notifications', 'demo'),
    (7, 'proxied_by', 'Component traffic is proxied by another component. Use cases: App from load balancer | App from API gateway', 'demo'),
    (8, 'authenticates_via', 'Component authenticates through another component. Use cases: Apps to identity providers | SSO relationships', 'demo'),
    (9, 'monitors', 'Component monitors another component. Use cases: Monitoring tools to infrastructure', 'demo'),
    (10, 'collaborates_with', 'Component collaborates with another component to deliver composite business functionality. Use cases: Distributed feature implementation | Multi-service workflows', 'demo'),
    (11, 'peers_with', 'Component operates as a peer with another component at the same architectural level. Use cases: Clustered applications | Load-balanced instances', 'demo'),
    (12, 'vm_guest_of', 'Component is a virtual machine guest of another component. Use cases: VM to hypervisor host', 'demo'),
    (13, 'load_balanced_by', 'Component traffic is load balanced by another component. Use cases: App servers behind load balancer', 'demo'),
    (14, 'communicates_with', 'Component has general communication with another component. Use cases: Generic network communication', 'demo'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

INSERT INTO component_protocols (protocol_id, protocol_name, description, created_by) VALUES
    (1, 'HTTP', 'Hypertext Transfer Protocol', 'demo'),
    (2, 'HTTPS', 'HTTP Secure', 'demo'),
    (3, 'TCP', 'Transmission Control Protocol', 'demo'),
    (4, 'UDP', 'User Datagram Protocol', 'demo'),
    (5, 'FTP', 'File Transfer Protocol', 'demo'),
    (6, 'FTPS', 'FTP Secure', 'demo'),
    (7, 'SFTP', 'SSH File Transfer Protocol', 'demo'),
    (8, 'SSH', 'Secure Shell', 'demo'),
    (9, 'Telnet', 'Telnet Protocol', 'demo'),
    (10, 'SMTP', 'Simple Mail Transfer Protocol', 'demo'),
    (11, 'SMTPS', 'SMTP Secure', 'demo'),
    (12, 'POP3', 'Post Office Protocol v3', 'demo'),
    (13, 'IMAP', 'Internet Message Access Protocol', 'demo'),
    (14, 'DNS', 'Domain Name System', 'demo'),
    (15, 'NTP', 'Network Time Protocol', 'demo'),
    (16, 'SNMP', 'Simple Network Management Protocol', 'demo'),
    (17, 'MySQL', 'MySQL Protocol', 'demo'),
    (18, 'PostgreSQL', 'PostgreSQL Protocol', 'demo'),
    (19, 'MSSQL', 'Microsoft SQL Server Protocol', 'demo'),
    (20, 'Oracle', 'Oracle Database Protocol', 'demo'),
    (21, 'SMB', 'Server Message Block', 'demo'),
    (22, 'NFS', 'Network File System', 'demo'),
    (23, 'RDP', 'Remote Desktop Protocol', 'demo'),
    (24, 'VNC', 'Virtual Network Computing', 'demo'),
    (25, 'TN3270', 'Telnet 3270', 'demo'),
    (26, 'TN5250', 'Telnet 5250', 'demo'),
    (999, '_PT_PENDING_', 'Placeholder for pending data discovery', 'demo'),
    (998, '_PT_NO_DATA_FOUND_', 'Placeholder when no data could be found', 'demo');

-- Grant permissions for demo schema
-- ==================================

-- Read-only user (bais_ro)
GRANT SELECT ON ALL TABLES IN SCHEMA demo TO bais_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA demo TO bais_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA demo 
    GRANT SELECT ON TABLES TO bais_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA demo 
    GRANT SELECT ON SEQUENCES TO bais_ro;

-- Read-write user (bais_rw)
-- Reference tables: SELECT only
GRANT SELECT ON demo.component_types TO bais_rw;
GRANT SELECT ON demo.component_abstraction_levels TO bais_rw;
GRANT SELECT ON demo.component_subtypes TO bais_rw;
GRANT SELECT ON demo.component_ops_statuses TO bais_rw;
GRANT SELECT ON demo.component_environments TO bais_rw;
GRANT SELECT ON demo.component_physical_locations TO bais_rw;
GRANT SELECT ON demo.component_relationship_types TO bais_rw;
GRANT SELECT ON demo.component_protocols TO bais_rw;
-- Business tables: Full CRUD
GRANT SELECT, INSERT, UPDATE, DELETE ON demo.biz_components TO bais_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON demo.biz_component_relationships TO bais_rw;
-- Grant sequence usage
GRANT USAGE ON ALL SEQUENCES IN SCHEMA demo TO bais_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA demo 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bais_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE rc34924 IN SCHEMA demo 
    GRANT USAGE ON SEQUENCES TO bais_rw;

-- ==================== END SECTION: SCHEMA:demo ====================

-- ==================== SECTION: PERMISSIONS ====================
-- Grant function execution permissions
-- All executed by rc34924 as the owner of all objects

-- Reset search path
SET search_path TO public;

-- Grant function execution permissions
-- =====================================
GRANT EXECUTE ON FUNCTION public.update_updated_column() TO bais_ro, bais_rw;

-- ==================== END SECTION: PERMISSIONS ====================

-- =====================================================================
-- Setup Complete!
-- 
-- Summary of what was created:
-- - 2 service users (bais_ro, bais_rw)
-- - 1 shared function (update_updated_column)
-- - 3 schemas (live, live_masked, demo)
-- - 10 tables per schema (8 reference + 2 business)
-- - Proper permissions for all users
-- - Data quality tracking with special values (_PT_PENDING_, _PT_NO_DATA_FOUND_)
-- - Record quality grading system for components
--
-- All objects are owned by rc34924
-- =====================================================================
