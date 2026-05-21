# G-Brain: Enterprise AI Intelligence Operating System

**The Company Brain** - Transform fragmented organizational knowledge into executable intelligence for autonomous AI agents.

## What is G-Brain?

G-Brain is a production-grade SaaS platform that converts invisible company knowledge into structured, executable intelligence for AI agents. It's not a chatbot, not enterprise search, and not just RAG—it's a complete operational AI system.

### The Problem

Companies run on invisible human memory:
- Tribal knowledge in slack channels
- Undocumented workflows in emails
- Decision patterns in ticket histories
- Operational heuristics in individual minds
- SOPs scattered across confluence
- Exception handling rules known only to veterans

AI systems today cannot access, understand, or execute on this knowledge.

### The Solution

G-Brain becomes:
- **Institutional memory layer**: Continuous knowledge ingestion & consolidation
- **Operational reasoning layer**: Understanding how work gets done
- **Executable workflow layer**: Converting knowledge to automated tasks
- **AI safety layer**: Governance, approvals, audits
- **Skill orchestration layer**: Powering autonomous agents

### The Output

A **Dynamic Company Skills Graph** that powers:
- AI employees (agents)
- Copilots
- Workflow automation
- Autonomous operations
- Decision support
- Enterprise-scale AI systems

---

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 16
- Neo4j 5.x
- Redis 7.x

### Local Development

```bash
# Clone and setup
git clone <repo>
cd company-brain
pnpm install

# Setup environment
cp .env.example .env
cp apps/api/.env.example apps/api/.env

# Start services
docker-compose up -d

# Run migrations
pnpm run db:migrate

# Start development servers
pnpm run dev
```

Access the platform:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- GraphQL: http://localhost:8000/graphql
- Neo4j Browser: http://localhost:7474

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│              Next.js 15 • React 19 • TypeScript                 │
├─────────────────────────────────────────────────────────────────┤
│                         API Gateway Layer                        │
│           Authentication • Rate Limiting • Routing               │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  Ingestion   │    Graph     │    Memory    │      Skills        │
│   Service    │   Service    │   Service    │      Service       │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│    Agent     │   Search     │  Governance  │    Orchestration   │
│   Service    │   Service    │   Service    │      Service       │
├──────────────┴──────────────┴──────────────┴────────────────────┤
│                      Task Queue (Celery)                        │
├─────────────────────────────────────────────────────────────────┤
│         PostgreSQL  │  Neo4j  │  Qdrant  │  Redis  │  S3       │
└─────────────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed design.

---

## Monorepo Structure

```
company-brain/
├── apps/
│   ├── web/                    # Frontend (Next.js)
│   ├── api/                    # Main API (FastAPI)
│   ├── workers/                # Async workers (Celery)
│   ├── agents/                 # Agent orchestration
│   └── gateway/                # API gateway
├── packages/
│   ├── ui/                     # Shared React components
│   ├── ai-core/                # AI/LLM utilities
│   ├── graph-engine/           # Knowledge graph operations
│   ├── workflow-engine/        # Workflow execution
│   ├── memory-engine/          # Memory consolidation
│   ├── connectors/             # Data source connectors
│   ├── auth/                   # Authentication utilities
│   └── shared/                 # Shared types & utils
├── infrastructure/
│   ├── terraform/              # IaC
│   ├── k8s/                    # Kubernetes manifests
│   └── docker/                 # Docker configurations
├── docs/                       # Documentation
├── scripts/                    # Setup & maintenance scripts
└── docker-compose.yml          # Local development stack
```

---

## Key Features

### 1. Universal Knowledge Ingestion
- **Multi-source connectors**: Email, Slack, Jira, Confluence, Salesforce, GitHub, databases, APIs
- **Incremental sync**: Efficient, event-driven updates
- **Entity extraction**: Automatic entity & relationship discovery
- **Permission mapping**: Enforce original access controls

### 2. Organizational Knowledge Graph
- **Multi-modal entities**: People, teams, workflows, incidents, products, etc.
- **Rich relationships**: Ownership, expertise, dependencies, escalation paths
- **Temporal tracking**: Version history, audit trails
- **Advanced queries**: Path finding, influence analysis, pattern detection

### 3. Intelligent Skill Extraction
- **Automatic workflow discovery**: Infer procedures from usage patterns
- **Decision tree extraction**: Learn how decisions are made
- **Heuristic learning**: Capture operational rules
- **Authority mapping**: Understand approval chains

### 4. Enterprise Agent Orchestration
- **Multi-agent collaboration**: Planner, executor, reviewer agents
- **Safe execution**: Approval gates, permission checks, audit trails
- **Memory integration**: Long-term context, procedural knowledge
- **Tool orchestration**: Seamless integration with enterprise systems

### 5. Advanced Search & Reasoning
- **Hybrid search**: Semantic + keyword + graph search
- **Explainable results**: Citations, provenance, confidence scores
- **Expertise discovery**: Find who knows what
- **Workflow search**: Find relevant procedures

### 6. Enterprise Governance
- **RBAC/ABAC**: Fine-grained access control
- **Approval workflows**: Configurable multi-level approvals
- **Audit trails**: Complete compliance logging
- **Policy enforcement**: Automated guardrails

---

## Technology Stack

**Frontend**: Next.js 15, React 19, TypeScript, Tailwind, shadcn/ui, Zustand, TanStack Query

**Backend**: Python FastAPI, FastAPI-GraphQL, Pydantic, SQLAlchemy, Alembic

**Databases**: PostgreSQL 16, Neo4j 5.x, Qdrant, Redis, ClickHouse

**AI/ML**: Claude, OpenAI, LangGraph, Custom orchestration, sentence-transformers

**Infrastructure**: Docker, Kubernetes, Terraform, GitHub Actions

**Observability**: OpenTelemetry, Langfuse, Prometheus, Grafana

---

## Development

### Setup Development Environment

```bash
# Install dependencies
pnpm install

# Build packages
pnpm run build

# Run development servers
pnpm run dev

# Run tests
pnpm run test

# Run linting
pnpm run lint
```

### Project Structure

```bash
# List apps
ls apps/

# List packages
ls packages/

# List infrastructure
ls infrastructure/
```

### Common Commands

```bash
# Database migrations
pnpm run db:migrate
pnpm run db:rollback

# Seed demo data
pnpm run db:seed

# Run tests
pnpm run test
pnpm run test:e2e

# Build for production
pnpm run build
```

---

## Deployment

### Docker Compose (Local Development)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Neo4j (ports 7687, 7474)
- Redis (port 6379)
- Qdrant (port 6333)
- API server (port 8000)
- Frontend (port 3000)

### Kubernetes (Production)

```bash
# Apply configurations
kubectl apply -f infrastructure/k8s/

# Check deployment
kubectl get pods
kubectl logs <pod-name>
```

See [infrastructure/k8s/README.md](./infrastructure/k8s/README.md) for details.

### Terraform (Cloud Infrastructure)

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

---

## API Documentation

### REST API

Complete REST API documentation at http://localhost:8000/docs

Key endpoints:
- `POST /api/v1/documents` - Ingest documents
- `GET /api/v1/graph/query` - Query knowledge graph
- `POST /api/v1/memory/store` - Store facts
- `GET /api/v1/search` - Search knowledge
- `POST /api/v1/agents/{id}/execute` - Execute agent tasks

### GraphQL API

GraphQL playground at http://localhost:8000/graphql

```graphql
query {
  organization(id: "org-123") {
    id
    name
    graph {
      nodes(limit: 10) {
        id
        type
        properties
      }
      edges(limit: 10) {
        source
        target
        type
      }
    }
  }
}
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md)

Development guidelines:
- Code style: Black (Python), ESLint (TypeScript)
- Testing: Pytest, Jest
- Documentation: MkDocs, Docstrings
- Commit messages: Conventional commits

---

## Documentation

- [Architecture](./ARCHITECTURE.md) - System design & decisions
- [API Reference](./docs/api-reference.md) - API documentation
- [Database Schema](./docs/database-schema.md) - Data models
- [Deployment Guide](./infrastructure/README.md) - Production setup
- [Connector Development](./packages/connectors/README.md) - Building connectors
- [Skill Extraction](./packages/ai-core/README.md) - Skill synthesis
- [Agent Development](./packages/ai-core/AGENTS.md) - Building agents

---

## Security

G-Brain is built with enterprise security in mind:

- **Encryption**: AES-256 at rest, TLS 1.3 in transit
- **RBAC/ABAC**: Fine-grained access control
- **Audit logging**: Complete compliance trails
- **SOC2 ready**: Designed for enterprise compliance
- **Data isolation**: Strict multi-tenancy
- **OIDC/SAML**: Enterprise SSO

See [SECURITY.md](./docs/SECURITY.md) for detailed security model.

---

## Performance

Target metrics:
- API latency: p95 < 200ms
- Graph queries: < 100ms
- Search: < 500ms
- Uptime: > 99.95%
- Agent success: > 95%

See [docs/PERFORMANCE.md](./docs/PERFORMANCE.md) for benchmarks.

---

## Roadmap

### Phase 1: Foundation ✅
- Core APIs
- Knowledge graph
- Basic ingestion
- Authentication

### Phase 2: Intelligence
- Skill extraction
- Memory consolidation
- Advanced graph querying
- Agent orchestration

### Phase 3: Autonomy
- Multi-agent systems
- Approval workflows
- Safety guardrails
- Operational insights

### Phase 4: Scale
- Optimization
- Analytics
- Enterprise deployment
- Marketplace

---

## Support

- **Issues**: Create an issue in GitHub
- **Documentation**: Read [docs/](./docs/)
- **Slack**: Join #g-brain-support in company Slack

---

## License

Proprietary - All rights reserved

---

## Authors

Principal Architect: Claude Code (Anthropic)

Built as a production-grade enterprise AI platform.
