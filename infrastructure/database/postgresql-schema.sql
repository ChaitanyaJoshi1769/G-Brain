-- G-Brain PostgreSQL Schema
-- Version: 1.0.0
-- This is the foundation schema for the G-Brain platform
-- All changes should be made via Alembic migrations, not direct SQL

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "hstore";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE organization_tier AS ENUM (
  'free',
  'starter',
  'professional',
  'enterprise'
);

CREATE TYPE user_role AS ENUM (
  'admin',
  'operator',
  'analyst',
  'viewer'
);

CREATE TYPE connection_type AS ENUM (
  'email',
  'slack',
  'jira',
  'confluence',
  'salesforce',
  'hubspot',
  'zendesk',
  'servicenow',
  'github',
  'gitlab',
  'linear',
  'asana',
  'monday',
  'notion',
  'google_drive',
  'sharepoint',
  'dropbox',
  'database',
  'api',
  'webhook'
);

CREATE TYPE sync_status AS ENUM (
  'idle',
  'syncing',
  'success',
  'partial_failure',
  'failed'
);

CREATE TYPE document_type AS ENUM (
  'email',
  'message',
  'ticket',
  'incident',
  'article',
  'procedure',
  'decision',
  'conversation',
  'code',
  'document',
  'meeting_notes',
  'transcript',
  'other'
);

CREATE TYPE entity_type AS ENUM (
  'person',
  'team',
  'department',
  'workflow',
  'task',
  'incident',
  'product',
  'service',
  'customer',
  'account',
  'system',
  'integration',
  'policy',
  'skill',
  'capability',
  'metric',
  'project',
  'vendor'
);

CREATE TYPE approval_status AS ENUM (
  'pending',
  'approved',
  'rejected',
  'escalated',
  'expired'
);

CREATE TYPE execution_status AS ENUM (
  'queued',
  'running',
  'success',
  'failure',
  'partial',
  'cancelled'
);

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Organizations (Multi-tenancy)
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  tier organization_tier NOT NULL DEFAULT 'starter',

  -- Configuration
  settings JSONB DEFAULT '{}',
  metadata JSONB DEFAULT '{}',

  -- Ownership
  owner_id UUID,

  -- Status
  is_active BOOLEAN DEFAULT true,
  is_archived BOOLEAN DEFAULT false,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP WITH TIME ZONE,

  CONSTRAINT valid_slug CHECK (slug ~ '^[a-z0-9-]+$')
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_owner_id ON organizations(owner_id);
CREATE INDEX idx_organizations_active ON organizations(is_active) WHERE is_active = true;

-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  avatar_url TEXT,

  -- Auth
  auth0_id VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255),

  -- Status
  is_active BOOLEAN DEFAULT true,
  email_verified BOOLEAN DEFAULT false,

  -- Settings
  preferences JSONB DEFAULT '{}',

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP WITH TIME ZONE,
  deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_auth0_id ON users(auth0_id);

-- Organization Members
CREATE TABLE organization_members (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  role user_role NOT NULL DEFAULT 'analyst',
  is_owner BOOLEAN DEFAULT false,

  -- Permissions
  permissions TEXT[] DEFAULT '{}',

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(organization_id, user_id)
);

CREATE INDEX idx_org_members_org_id ON organization_members(organization_id);
CREATE INDEX idx_org_members_user_id ON organization_members(user_id);

-- Workspaces (Org subdivisions)
CREATE TABLE workspaces (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL,
  description TEXT,

  settings JSONB DEFAULT '{}',
  metadata JSONB DEFAULT '{}',

  is_active BOOLEAN DEFAULT true,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(organization_id, slug)
);

CREATE INDEX idx_workspaces_org_id ON workspaces(organization_id);

-- =============================================================================
-- CONNECTORS & INTEGRATIONS
-- =============================================================================

-- Data Connectors
CREATE TABLE connectors (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,

  name VARCHAR(255) NOT NULL,
  connector_type connection_type NOT NULL,

  -- Authentication
  credentials BYTEA,  -- encrypted
  credentials_encrypted BOOLEAN DEFAULT true,

  -- Configuration
  config JSONB DEFAULT '{}',

  -- Status
  status sync_status DEFAULT 'idle',
  last_sync_at TIMESTAMP WITH TIME ZONE,
  last_error TEXT,

  -- Sync settings
  auto_sync BOOLEAN DEFAULT true,
  sync_frequency_minutes INTEGER DEFAULT 60,

  is_active BOOLEAN DEFAULT true,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT valid_name CHECK (length(name) > 0)
);

CREATE INDEX idx_connectors_org_id ON connectors(organization_id);
CREATE INDEX idx_connectors_workspace_id ON connectors(workspace_id);
CREATE INDEX idx_connectors_type ON connectors(connector_type);
CREATE INDEX idx_connectors_active ON connectors(is_active) WHERE is_active = true;

-- Sync History
CREATE TABLE sync_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  connector_id UUID NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,

  status sync_status NOT NULL,
  documents_processed INTEGER DEFAULT 0,
  documents_created INTEGER DEFAULT 0,
  documents_updated INTEGER DEFAULT 0,
  documents_skipped INTEGER DEFAULT 0,

  errors_count INTEGER DEFAULT 0,
  error_details JSONB,

  started_at TIMESTAMP WITH TIME ZONE NOT NULL,
  completed_at TIMESTAMP WITH TIME ZONE,
  duration_seconds INTEGER,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sync_history_connector_id ON sync_history(connector_id);
CREATE INDEX idx_sync_history_created_at ON sync_history(created_at);

-- =============================================================================
-- DOCUMENTS & INGESTION
-- =============================================================================

-- Documents (raw ingested content)
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  connector_id UUID REFERENCES connectors(id),

  external_id VARCHAR(255),  -- source system ID

  title VARCHAR(500),
  content TEXT,
  raw_content BYTEA,  -- compressed

  document_type document_type DEFAULT 'document',
  mime_type VARCHAR(100),

  -- Metadata
  author_id UUID REFERENCES users(id),
  author_name VARCHAR(255),
  author_email VARCHAR(255),

  created_source_at TIMESTAMP WITH TIME ZONE,
  updated_source_at TIMESTAMP WITH TIME ZONE,

  source_url TEXT,
  source_metadata JSONB,

  -- Processing
  content_hash VARCHAR(64),
  is_duplicate BOOLEAN DEFAULT false,
  is_processed BOOLEAN DEFAULT false,
  processing_error TEXT,

  -- Access control
  permissions_encrypted BYTEA,  -- encrypted JSON

  tags TEXT[] DEFAULT '{}',

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_documents_org_id ON documents(organization_id);
CREATE INDEX idx_documents_workspace_id ON documents(workspace_id);
CREATE INDEX idx_documents_connector_id ON documents(connector_id);
CREATE INDEX idx_documents_external_id ON documents(external_id);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_gin_tags ON documents USING GIN(tags);

-- Document Chunks (for embedding & retrieval)
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

  content TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,

  tokens_count INTEGER,

  -- Embeddings
  embedding_model VARCHAR(100),
  embedding_vector FLOAT8[] NOT NULL,

  -- Metadata
  metadata JSONB DEFAULT '{}',

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_vector ON document_chunks USING ivfflat(embedding_vector);

-- =============================================================================
-- ENTITIES & RELATIONSHIPS
-- =============================================================================

-- Entities (normalized from documents)
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  external_id VARCHAR(255),

  name VARCHAR(255) NOT NULL,
  entity_type entity_type NOT NULL,

  description TEXT,

  -- Properties
  properties JSONB DEFAULT '{}',

  -- Graph reference
  graph_node_id VARCHAR(255),

  -- Relationships
  parent_entity_id UUID REFERENCES entities(id),

  -- Confidence
  extraction_confidence FLOAT DEFAULT 1.0,

  -- Status
  is_verified BOOLEAN DEFAULT false,
  is_auto_merged BOOLEAN DEFAULT false,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT valid_confidence CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1)
);

CREATE INDEX idx_entities_org_id ON entities(organization_id);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_external_id ON entities(external_id);
CREATE INDEX idx_entities_graph_node_id ON entities(graph_node_id);

-- Entity Mappings (deduplication)
CREATE TABLE entity_mappings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,

  confidence FLOAT DEFAULT 0.9,
  reason TEXT,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(source_entity_id, target_entity_id),
  CONSTRAINT different_entities CHECK (source_entity_id != target_entity_id)
);

-- =============================================================================
-- SKILLS & WORKFLOWS
-- =============================================================================

-- Skills (executable AI capabilities)
CREATE TABLE skills (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  name VARCHAR(255) NOT NULL,
  description TEXT,
  category VARCHAR(100),

  -- Skill definition
  skill_definition JSONB NOT NULL,  -- schema, steps, decision points

  input_schema JSONB,
  output_schema JSONB,

  -- Execution
  executable BOOLEAN DEFAULT true,
  implementation_url TEXT,

  -- Metadata
  owner_id UUID REFERENCES users(id),
  owner_team_id UUID,

  -- Versioning
  version VARCHAR(20) DEFAULT '1.0.0',
  parent_skill_id UUID REFERENCES skills(id),

  -- Confidence
  extraction_confidence FLOAT DEFAULT 0.5,
  execution_success_rate FLOAT DEFAULT 0.0,
  times_executed INTEGER DEFAULT 0,

  -- Status
  is_published BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,

  -- Tags & metadata
  tags TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}',

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT valid_confidence CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
  CONSTRAINT valid_success_rate CHECK (execution_success_rate >= 0 AND execution_success_rate <= 1)
);

CREATE INDEX idx_skills_org_id ON skills(organization_id);
CREATE INDEX idx_skills_category ON skills(category);
CREATE INDEX idx_skills_owner_id ON skills(owner_id);
CREATE INDEX idx_skills_active ON skills(is_active) WHERE is_active = true;
CREATE INDEX idx_skills_published ON skills(is_published) WHERE is_published = true;

-- Skill Invocations (execution history)
CREATE TABLE skill_invocations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  agent_id UUID,  -- executing agent
  user_id UUID REFERENCES users(id),

  input_params JSONB,
  output_result JSONB,

  status execution_status NOT NULL,
  error_message TEXT,

  duration_ms INTEGER,
  tokens_used INTEGER,
  cost_cents INTEGER,

  approval_required BOOLEAN DEFAULT false,
  approval_id UUID,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_invocations_skill_id ON skill_invocations(skill_id);
CREATE INDEX idx_skill_invocations_org_id ON skill_invocations(organization_id);
CREATE INDEX idx_skill_invocations_user_id ON skill_invocations(user_id);
CREATE INDEX idx_skill_invocations_created_at ON skill_invocations(created_at);
CREATE INDEX idx_skill_invocations_status ON skill_invocations(status);

-- =============================================================================
-- AGENTS & ORCHESTRATION
-- =============================================================================

-- AI Agents
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  name VARCHAR(255) NOT NULL,
  description TEXT,

  agent_type VARCHAR(50),  -- planner, executor, reviewer, coordinator

  -- Configuration
  system_prompt TEXT,
  model_name VARCHAR(100),
  temperature FLOAT DEFAULT 0.7,
  max_tokens INTEGER DEFAULT 4096,

  -- Capabilities
  skill_ids UUID[] DEFAULT '{}',
  tool_ids UUID[] DEFAULT '{}',

  -- Memory
  has_memory BOOLEAN DEFAULT true,
  memory_size_tokens INTEGER DEFAULT 8000,

  -- Guardrails
  require_approval BOOLEAN DEFAULT false,
  approval_threshold FLOAT DEFAULT 0.8,
  max_iterations INTEGER DEFAULT 10,
  timeout_seconds INTEGER DEFAULT 300,

  -- Monitoring
  success_rate FLOAT DEFAULT 0.0,
  times_executed INTEGER DEFAULT 0,

  is_active BOOLEAN DEFAULT true,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_org_id ON agents(organization_id);
CREATE INDEX idx_agents_active ON agents(is_active) WHERE is_active = true;

-- Agent Executions
CREATE TABLE agent_executions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  user_id UUID REFERENCES users(id),

  input_task TEXT NOT NULL,
  output_result JSONB,

  status execution_status NOT NULL,
  error_message TEXT,

  duration_ms INTEGER,
  tokens_used INTEGER,
  cost_cents INTEGER,

  -- Chain of thought
  execution_trace JSONB,

  -- Approval
  required_approvals INTEGER DEFAULT 0,
  pending_approvals INTEGER DEFAULT 0,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_executions_agent_id ON agent_executions(agent_id);
CREATE INDEX idx_agent_executions_org_id ON agent_executions(organization_id);
CREATE INDEX idx_agent_executions_user_id ON agent_executions(user_id);
CREATE INDEX idx_agent_executions_status ON agent_executions(status);
CREATE INDEX idx_agent_executions_created_at ON agent_executions(created_at);

-- =============================================================================
-- MEMORY SYSTEM
-- =============================================================================

-- Episodic Memory (events)
CREATE TABLE episodic_memory (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  agent_id UUID REFERENCES agents(id),

  event_type VARCHAR(100) NOT NULL,
  description TEXT,

  source_document_id UUID REFERENCES documents(id),
  source_entity_id UUID REFERENCES entities(id),

  metadata JSONB DEFAULT '{}',

  relevance_score FLOAT DEFAULT 1.0,
  confidence FLOAT DEFAULT 1.0,

  expires_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_episodic_memory_org_id ON episodic_memory(organization_id);
CREATE INDEX idx_episodic_memory_agent_id ON episodic_memory(agent_id);
CREATE INDEX idx_episodic_memory_event_type ON episodic_memory(event_type);
CREATE INDEX idx_episodic_memory_created_at ON episodic_memory(created_at);

-- Semantic Memory (facts)
CREATE TABLE semantic_memory (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  fact_type VARCHAR(100) NOT NULL,
  subject VARCHAR(255),
  predicate VARCHAR(255),
  object TEXT,

  source_ids UUID[] DEFAULT '{}',  -- document/entity sources

  relevance_score FLOAT DEFAULT 1.0,
  confidence FLOAT DEFAULT 1.0,
  frequency_count INTEGER DEFAULT 1,

  last_accessed_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_semantic_memory_org_id ON semantic_memory(organization_id);
CREATE INDEX idx_semantic_memory_fact_type ON semantic_memory(fact_type);
CREATE INDEX idx_semantic_memory_subject ON semantic_memory(subject);

-- =============================================================================
-- APPROVALS & GOVERNANCE
-- =============================================================================

-- Approval Requests
CREATE TABLE approval_requests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  request_type VARCHAR(100) NOT NULL,  -- skill_execution, agent_execution, etc
  request_resource_id UUID,

  requester_id UUID REFERENCES users(id),

  title VARCHAR(255),
  description TEXT,

  required_approvers UUID[] DEFAULT '{}',
  approvers_completed UUID[] DEFAULT '{}',

  status approval_status NOT NULL DEFAULT 'pending',

  reason_for_rejection TEXT,

  metadata JSONB DEFAULT '{}',

  expires_at TIMESTAMP WITH TIME ZONE,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_approvals_org_id ON approval_requests(organization_id);
CREATE INDEX idx_approvals_status ON approval_requests(status);
CREATE INDEX idx_approvals_requester_id ON approval_requests(requester_id);
CREATE INDEX idx_approvals_created_at ON approval_requests(created_at);

-- Approval History
CREATE TABLE approval_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  approval_request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,

  approver_id UUID NOT NULL REFERENCES users(id),
  decision VARCHAR(20) NOT NULL,  -- approved, rejected, escalated

  comment TEXT,
  metadata JSONB DEFAULT '{}',

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_approval_history_request_id ON approval_history(approval_request_id);

-- =============================================================================
-- AUDIT & COMPLIANCE
-- =============================================================================

-- Audit Logs
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  actor_id UUID REFERENCES users(id),
  action VARCHAR(100) NOT NULL,

  resource_type VARCHAR(100),
  resource_id UUID,

  changes JSONB,  -- before/after
  metadata JSONB DEFAULT '{}',

  ip_address INET,
  user_agent TEXT,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_org_id ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- =============================================================================
-- ANALYTICS & METRICS
-- =============================================================================

-- Daily Organization Stats
CREATE TABLE organization_stats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  stat_date DATE NOT NULL,

  -- Ingestion
  documents_ingested INTEGER DEFAULT 0,
  documents_total INTEGER DEFAULT 0,

  -- Skills
  skills_total INTEGER DEFAULT 0,
  skills_executed INTEGER DEFAULT 0,

  -- Agents
  agents_total INTEGER DEFAULT 0,
  agent_executions INTEGER DEFAULT 0,
  agent_success_count INTEGER DEFAULT 0,

  -- Approvals
  approvals_created INTEGER DEFAULT 0,
  approvals_completed INTEGER DEFAULT 0,

  -- Cost
  total_tokens_used BIGINT DEFAULT 0,
  estimated_cost_cents INTEGER DEFAULT 0,

  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  UNIQUE(organization_id, stat_date)
);

CREATE INDEX idx_org_stats_date ON organization_stats(stat_date);
CREATE INDEX idx_org_stats_org_id ON organization_stats(organization_id);

-- =============================================================================
-- SYSTEM TABLES
-- =============================================================================

-- Schema Versions
CREATE TABLE schema_versions (
  id INTEGER PRIMARY KEY,
  version_number VARCHAR(20) NOT NULL UNIQUE,
  applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  description TEXT
);

-- System Configuration
CREATE TABLE system_config (
  key VARCHAR(255) PRIMARY KEY,
  value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TRIGGERS & MAINTENANCE
-- =============================================================================

-- Update timestamps on modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_skills_updated_at BEFORE UPDATE ON skills
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

INSERT INTO schema_versions (id, version_number, description)
VALUES (1, '1.0.0', 'Initial G-Brain schema');
