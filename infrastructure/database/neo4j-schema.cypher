// G-Brain Neo4j Knowledge Graph Schema
// Version: 1.0.0
// This file defines the graph structure for organizational knowledge

// =============================================================================
// CONSTRAINTS
// =============================================================================

// Uniqueness Constraints
CREATE CONSTRAINT unique_person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT unique_team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT unique_workflow_id IF NOT EXISTS FOR (w:Workflow) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT unique_incident_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT unique_skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT unique_system_id IF NOT EXISTS FOR (sys:System) REQUIRE sys.id IS UNIQUE;
CREATE CONSTRAINT unique_decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT unique_product_id IF NOT EXISTS FOR (prod:Product) REQUIRE prod.id IS UNIQUE;

// Existence Constraints
CREATE CONSTRAINT exists_person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS NOT NULL;
CREATE CONSTRAINT exists_team_name IF NOT EXISTS FOR (t:Team) REQUIRE t.name IS NOT NULL;
CREATE CONSTRAINT exists_workflow_name IF NOT EXISTS FOR (w:Workflow) REQUIRE w.name IS NOT NULL;

// =============================================================================
// INDEXES
// =============================================================================

// Person Indexes
CREATE INDEX idx_person_email IF NOT EXISTS FOR (p:Person) ON (p.email);
CREATE INDEX idx_person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX idx_person_org_id IF NOT EXISTS FOR (p:Person) ON (p.organization_id);

// Team Indexes
CREATE INDEX idx_team_name IF NOT EXISTS FOR (t:Team) ON (t.name);
CREATE INDEX idx_team_org_id IF NOT EXISTS FOR (t:Team) ON (t.organization_id);

// Workflow Indexes
CREATE INDEX idx_workflow_name IF NOT EXISTS FOR (w:Workflow) ON (w.name);
CREATE INDEX idx_workflow_category IF NOT EXISTS FOR (w:Workflow) ON (w.category);

// Skill Indexes
CREATE INDEX idx_skill_name IF NOT EXISTS FOR (s:Skill) ON (s.name);
CREATE INDEX idx_skill_category IF NOT EXISTS FOR (s:Skill) ON (s.category);

// System Indexes
CREATE INDEX idx_system_name IF NOT EXISTS FOR (sys:System) ON (sys.name);

// Generic Indexes
CREATE INDEX idx_node_created_at IF NOT EXISTS FOR (n) ON (n.created_at);
CREATE INDEX idx_node_org_id IF NOT EXISTS FOR (n) ON (n.organization_id);

// =============================================================================
// NODE LABELS & PROPERTIES
// =============================================================================

// Person Node
// Properties: id, name, email, role, org_id, department, avatar_url,
//            expertise[], active, created_at, updated_at, external_id
CALL db.labels() YIELD label
WHERE label = "Person"
RETURN label;

// Team Node
// Properties: id, name, org_id, description, lead_id, department,
//            team_type, size, created_at, updated_at, external_id
CALL db.labels() YIELD label
WHERE label = "Team"
RETURN label;

// Department Node
// Properties: id, name, org_id, description, budget, lead_id,
//            created_at, updated_at
CALL db.labels() YIELD label
WHERE label = "Department"
RETURN label;

// Workflow Node
// Properties: id, name, org_id, description, category, status,
//            owner_id, complexity, avg_duration_min, success_rate,
//            times_executed, created_at, updated_at, external_id
CALL db.labels() YIELD label
WHERE label = "Workflow"
RETURN label;

// Task Node
// Properties: id, name, workflow_id, org_id, sequence, description,
//            approval_required, depends_on[], created_at, updated_at
CALL db.labels() YIELD label
WHERE label = "Task"
RETURN label;

// Incident Node
// Properties: id, title, org_id, description, status, severity,
//            affected_systems[], impact_users, root_cause, resolved_at,
//            created_at, updated_at, external_id
CALL db.labels() YIELD label
WHERE label = "Incident"
RETURN label;

// Resolution Node
// Properties: id, incident_id, org_id, solution, steps[], tools_used[],
//            author_id, implemented_at, created_at
CALL db.labels() YIELD label
WHERE label = "Resolution"
RETURN label;

// Skill Node
// Properties: id, name, org_id, category, description, executable,
//            success_rate, times_executed, owner_id, created_at, updated_at
CALL db.labels() YIELD label
WHERE label = "Skill"
RETURN label;

// System Node
// Properties: id, name, org_id, description, system_type, url,
//            owner_id, criticality, created_at, updated_at, external_id
CALL db.labels() YIELD label
WHERE label = "System"
RETURN label;

// Decision Node
// Properties: id, title, org_id, context, decision, rationale,
//            decision_maker_id, decided_at, created_at
CALL db.labels() YIELD label
WHERE label = "Decision"
RETURN label;

// Policy Node
// Properties: id, title, org_id, content, policy_type, owner_id,
//            effective_date, created_at, updated_at
CALL db.labels() YIELD label
WHERE label = "Policy"
RETURN label;

// Product Node
// Properties: id, name, org_id, description, owner_id, launch_date,
//            revenue, customers[], created_at, updated_at
CALL db.labels() YIELD label
WHERE label = "Product"
RETURN label;

// Customer Node
// Properties: id, name, org_id, industry, contract_value, account_manager_id,
//            health_score, created_at, updated_at, external_id
CALL db.labels() YIELD label
WHERE label = "Customer"
RETURN label;

// Vendor Node
// Properties: id, name, org_id, vendor_type, contact, cost_yearly,
//            renewal_date, created_at, updated_at, external_id
CALL db.labels() YIELD label
WHERE label = "Vendor"
RETURN label;

// Metric Node
// Properties: id, name, org_id, metric_type, description, owner_id,
//            current_value, target_value, unit, created_at, updated_at
CALL db.labels() YIELD label
WHERE label = "Metric"
RETURN label;

// =============================================================================
// RELATIONSHIP TYPES & SEMANTICS
// =============================================================================

// Person Relationships
// MANAGES_PERSON -> Person (direct report)
// MANAGES_TEAM -> Team
// MEMBER_OF -> Team
// MEMBER_OF -> Department
// EXPERT_IN -> Skill
// KNOWS -> Person (knows another person)
// WORKS_ON -> Workflow
// WORKS_ON -> Incident
// RESOLVES -> Incident
// RESPONSIBLE_FOR -> System
// RESPONSIBLE_FOR -> Policy
// OWNS -> Skill
// OWNS -> Workflow
// APPROVES -> Decision
// AUTHORED -> Decision
// MANAGED_BY -> ?
// REPORTS_TO -> Person

// Team Relationships
// MANAGES -> Team (parent team)
// MEMBER_OF -> Department
// OWNS -> Workflow
// RESPONSIBLE_FOR -> System
// RESPONSIBLE_FOR -> Product
// USES -> System
// SUPPORTS -> Customer

// Workflow Relationships
// HAS_TASK -> Task
// PRODUCES -> Outcome
// USES -> System
// REQUIRES_SKILL -> Skill
// DEPENDS_ON -> Workflow
// RELATED_TO -> Incident

// Task Relationships
// PART_OF -> Workflow
// REQUIRES_APPROVAL_FROM -> Person
// DEPENDS_ON -> Task
// USES -> System
// REQUIRES_SKILL -> Skill

// Incident Relationships
// AFFECTED_SYSTEM -> System
// HAS_RESOLUTION -> Resolution
// CAUSED_BY -> Incident
// RELATED_TO -> Workflow
// IDENTIFIED_BY -> Person

// Decision Relationships
// RELATED_TO -> Workflow
// RELATED_TO -> Incident
// IMPACTS -> System
// IMPACTS -> Team
// IMPLEMENTS -> Policy

// Skill Relationships
// REQUIRED_FOR -> Task
// REQUIRED_FOR -> Workflow
// SIMILAR_TO -> Skill
// DEPENDS_ON -> Skill
// USED_IN -> Incident

// =============================================================================
// INITIALIZATION QUERIES
// =============================================================================

// Create organization root node (example)
CREATE (org:Organization {
  id: "org-root",
  name: "Root Organization",
  created_at: timestamp(),
  updated_at: timestamp()
});

// Create sample Department
MATCH (org:Organization {id: "org-root"})
CREATE (dept:Department {
  id: "dept-engineering",
  name: "Engineering",
  description: "Software Engineering Department",
  organization_id: "org-root",
  created_at: timestamp(),
  updated_at: timestamp()
})
WITH org, dept
CREATE (org)-[:HAS_DEPARTMENT]->(dept);

// Create sample Team
MATCH (dept:Department {id: "dept-engineering"})
CREATE (team:Team {
  id: "team-backend",
  name: "Backend Team",
  organization_id: "org-root",
  department: "Engineering",
  team_type: "engineering",
  size: 5,
  created_at: timestamp(),
  updated_at: timestamp()
})
WITH dept, team
CREATE (dept)-[:HAS_TEAM]->(team);

// Create sample Person
CREATE (person:Person {
  id: "person-alice",
  name: "Alice Engineer",
  email: "alice@company.com",
  role: "Senior Engineer",
  organization_id: "org-root",
  department: "Engineering",
  expertise: ["Python", "PostgreSQL", "AWS"],
  active: true,
  created_at: timestamp(),
  updated_at: timestamp()
});

// Create sample Workflow
CREATE (workflow:Workflow {
  id: "workflow-deployment",
  name: "Production Deployment",
  organization_id: "org-root",
  category: "operations",
  status: "active",
  complexity: "high",
  avg_duration_min: 30,
  success_rate: 0.95,
  times_executed: 247,
  created_at: timestamp(),
  updated_at: timestamp()
});

// Create sample Skill
CREATE (skill:Skill {
  id: "skill-refund-processing",
  name: "Refund Processing",
  organization_id: "org-root",
  category: "customer-operations",
  description: "Process customer refunds with appropriate escalation",
  executable: true,
  success_rate: 0.94,
  times_executed: 1523,
  created_at: timestamp(),
  updated_at: timestamp()
});

// Create sample System
CREATE (system:System {
  id: "system-salesforce",
  name: "Salesforce CRM",
  organization_id: "org-root",
  system_type: "crm",
  url: "https://company.salesforce.com",
  criticality: "critical",
  created_at: timestamp(),
  updated_at: timestamp()
});

// =============================================================================
// RELATIONSHIP PATTERNS (Examples)
// =============================================================================

// Connect Person to Team
MATCH (person:Person {id: "person-alice"}), (team:Team {id: "team-backend"})
CREATE (person)-[:MEMBER_OF]->(team);

// Connect Person to Skill
MATCH (person:Person {id: "person-alice"}), (skill:Skill {id: "skill-refund-processing"})
CREATE (person)-[:EXPERT_IN {confidence: 0.9, years_of_experience: 5}]->(skill);

// Connect Workflow to Skill
MATCH (workflow:Workflow {id: "workflow-deployment"}), (skill:Skill {id: "skill-refund-processing"})
CREATE (workflow)-[:REQUIRES_SKILL {required: true}]->(skill);

// Connect Team to System
MATCH (team:Team {id: "team-backend"}), (system:System {id: "system-salesforce"})
CREATE (team)-[:USES {owner: false, access_level: "read"}]->(system);

// =============================================================================
// GRAPH QUERIES (Reference)
// =============================================================================

// Query: Get all people in a team
// MATCH (team:Team {id: "team-backend"})-[:MEMBER_OF]-(person:Person)
// RETURN person.name, person.expertise;

// Query: Get expertise graph for a person
// MATCH (person:Person {id: "person-alice"})-[:EXPERT_IN]->(skill:Skill)
// RETURN person.name, skill.name, skill.category;

// Query: Get workflow dependencies
// MATCH path=(w:Workflow)-[:DEPENDS_ON*]->(dependency:Workflow)
// WHERE w.id = "workflow-deployment"
// RETURN path;

// Query: Find similar workflows
// MATCH (workflow:Workflow {id: "workflow-deployment"})-[:REQUIRES_SKILL]->(skill:Skill)
// MATCH (similar:Workflow)-[:REQUIRES_SKILL]->(skill)
// WHERE similar.id != workflow.id
// RETURN similar.name, count(skill) as shared_skills
// ORDER BY shared_skills DESC;

// Query: Get incident resolution patterns
// MATCH (incident:Incident)-[:HAS_RESOLUTION]->(resolution:Resolution)
// MATCH (resolution)-[:USES_SKILL]->(skill:Skill)
// RETURN incident.title, skill.name, count(*) as frequency
// ORDER BY frequency DESC;

// Query: Find experts for a skill
// MATCH (person:Person)-[:EXPERT_IN {confidence: score}]->(skill:Skill {id: "skill-id"})
// WHERE score > 0.7
// RETURN person.name, person.email, score
// ORDER BY score DESC;

// Query: Impact analysis
// MATCH (system:System {id: "system-id"})-[:REQUIRED_FOR]-(task:Task)-[:PART_OF]->(workflow:Workflow)
// RETURN DISTINCT workflow.name;

// =============================================================================
// END OF SCHEMA
// =============================================================================

// This schema is designed to support:
// 1. Organizational structure (People, Teams, Departments)
// 2. Workflow understanding (Workflows, Tasks, Dependencies)
// 3. Knowledge representation (Skills, Expertise)
// 4. System integration mapping (Systems, integrations)
// 5. Incident management (Incidents, Resolutions)
// 6. Decision tracking (Decisions, Impacts)
// 7. Advanced queries (paths, influence, expertise discovery)

// The graph is optimized for:
// - Fast relationship traversal
// - Pattern matching (finding similar workflows, expertise paths)
// - Influence analysis (what impacts what)
// - Expert discovery (who knows what)
// - Root cause analysis (tracing incident causes)
// - Workflow optimization (identifying bottlenecks)
