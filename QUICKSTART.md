# G-Brain Quick Start Guide

## 1 Minute Setup

```bash
# Clone & setup
git clone <repo> company-brain
cd company-brain

# Copy environment config
cp .env.example .env

# Start everything
docker-compose up -d

# Access services
open http://localhost:3000          # Frontend
open http://localhost:8000/docs     # API Docs
open http://localhost:7474          # Neo4j
open http://localhost:3001          # Grafana
```

## 5 Minute Deep Dive

### Install Dependencies
```bash
pnpm install
```

### Database Setup
```bash
# Run migrations
pnpm run db:migrate

# Seed demo data
pnpm run db:seed
```

### Start Development
```bash
# Terminal 1: Backend + Frontend
pnpm run dev

# Terminal 2: Watch logs
docker-compose logs -f

# Terminal 3: Run tests
pnpm run test
```

### Check Everything Works
```bash
# Test API
curl http://localhost:8000/health
# Response: {"status":"ok","service":"gbrain-api",...}

# Check databases
curl http://localhost:8000/health/ready
# Should show all checks as "ok"
```

---

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | Web UI |
| API | http://localhost:8000 | Backend API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Neo4j Browser | http://localhost:7474 | Graph DB UI |
| PostgreSQL | localhost:5432 | Relational DB |
| Redis | localhost:6379 | Cache |
| Qdrant | http://localhost:6333 | Vector DB |
| MinIO | http://localhost:9000 | Object Storage |
| MinIO Console | http://localhost:9001 | S3 Console |
| Celery Flower | http://localhost:5555 | Task Monitoring |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3001 | Dashboards |

---

## Essential Commands

### Development
```bash
pnpm run dev              # Start all services
pnpm run build            # Build all apps
pnpm run test             # Run tests
pnpm run lint             # Lint code
pnpm run format           # Format code
pnpm run typecheck        # Type checking
```

### Database
```bash
pnpm run db:migrate       # Run migrations
pnpm run db:rollback      # Rollback one migration
pnpm run db:seed          # Seed demo data
pnpm run db:drop          # Drop all tables
```

### Docker
```bash
docker-compose up -d      # Start services
docker-compose down       # Stop services
docker-compose logs -f    # View logs
docker-compose ps         # Check status
docker-compose down -v    # Clean everything
```

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# API docs (interactive)
open http://localhost:8000/docs
```

---

## Common Issues & Solutions

### Port Already in Use
```bash
# Find process using port
lsof -i :3000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
pnpm run db:migrate
```

### Neo4j Not Accessible
```bash
# Check Neo4j health
curl http://localhost:7474/db/neo4j/

# View logs
docker-compose logs neo4j

# Reset Neo4j
docker-compose down neo4j
docker volume rm company-brain_neo4j_data
docker-compose up -d neo4j
```

### API Not Responding
```bash
# Check API logs
docker-compose logs api

# Restart API
docker-compose restart api

# Rebuild if needed
docker-compose up -d --build api
```

---

## Project Structure

```
company-brain/
├── apps/api/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Settings
│   │   ├── database.py       # DB connections
│   │   ├── middleware.py     # Middleware
│   │   ├── exception_handlers.py
│   │   ├── observability.py
│   │   └── routers/          # API endpoints
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── tests/
├── apps/web/                  # Next.js frontend (todo)
├── infrastructure/
│   ├── database/
│   │   ├── postgresql-schema.sql
│   │   └── neo4j-schema.cypher
│   ├── terraform/             # IaC (todo)
│   └── k8s/                   # Kubernetes (todo)
├── docker-compose.yml
├── README.md
├── ARCHITECTURE.md
└── PHASE_1_README.md
```

---

## Development Workflow

### Adding a New API Endpoint

1. **Create router file** in `apps/api/app/routers/`
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/example")
async def example():
    return {"status": "ok"}
```

2. **Register in main.py**
```python
from app.routers import example
app.include_router(example.router, prefix="/api/v1/example")
```

3. **Test**
```bash
curl http://localhost:8000/api/v1/example
```

### Adding a Database Migration

1. **Create migration file**
```bash
cd apps/api
alembic revision --autogenerate -m "add_column_to_users"
```

2. **Edit migration file** in `alembic/versions/`

3. **Apply migration**
```bash
pnpm run db:migrate
```

### Adding a New Service

1. **Create app in apps/**
2. **Add to docker-compose.yml**
3. **Register in turbo.json**
4. **Update scripts in package.json**

---

## Environment Configuration

Key variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://...
NEO4J_URI=neo4j://...

# API
API_PORT=8000
DEBUG=true

# Security
SECRET_KEY=your-secret-here
CORS_ORIGINS=[...]

# LLM Providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

See `.env.example` for all options.

---

## Deployment

### Local (Docker Compose)
```bash
docker-compose up -d
```

### Cloud (Kubernetes)
```bash
cd infrastructure/k8s
kubectl apply -f .
```

### Cloud (Terraform)
```bash
cd infrastructure/terraform
terraform init
terraform apply
```

---

## Monitoring & Debugging

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Follow new logs
docker-compose logs -f --tail=100
```

### Database Inspection

**PostgreSQL:**
```bash
# Connect
psql -h localhost -U gbrain_user -d gbrain

# List tables
\dt

# Query data
SELECT * FROM organizations LIMIT 5;
```

**Neo4j:**
```bash
# Visit http://localhost:7474
# Credentials: neo4j / gbrain_password

# Query graph
MATCH (p:Person) RETURN p LIMIT 5;
```

**Redis:**
```bash
# Connect
redis-cli -h localhost -p 6379 -a gbrain_password

# Check keys
KEYS *

# Get value
GET key_name
```

### Performance Profiling

```bash
# Check database slow queries
docker exec gbrain-postgres psql -U gbrain_user -d gbrain \
  -c "SELECT * FROM pg_stat_statements LIMIT 10;"

# Check Redis memory
redis-cli -a gbrain_password INFO memory

# View API metrics
open http://localhost:9090
```

---

## Testing

### Run Tests
```bash
# All tests
pnpm run test

# Specific test
pnpm run test -- app/routers/health.test.py

# With coverage
pnpm run test:cov

# E2E tests
pnpm run test:e2e
```

### Write Tests
```python
# tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

---

## Documentation

- **README.md** - Project overview
- **ARCHITECTURE.md** - System design (read this first!)
- **PHASE_1_README.md** - Phase 1 guide
- **IMPLEMENTATION_SUMMARY.md** - What was created
- **Code comments** - Inline documentation
- **API docs** - Interactive at /docs

---

## Getting Help

1. **Check documentation** in README.md and ARCHITECTURE.md
2. **Read code comments** - well documented
3. **Check error logs** - docker-compose logs -f
4. **Search issues** - GitHub issues
5. **Ask team** - Slack channel

---

## Next Steps

1. ✅ Read ARCHITECTURE.md
2. ✅ Run `docker-compose up -d`
3. ✅ Visit http://localhost:3000
4. ✅ Check API docs at http://localhost:8000/docs
5. ⏭️  Start Phase 2 (Skill Extraction)

---

## Quick Reference

| Task | Command |
|------|---------|
| Start dev | `pnpm run dev` |
| Stop services | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Database migrations | `pnpm run db:migrate` |
| Run tests | `pnpm run test` |
| Build for production | `pnpm run build` |
| Lint code | `pnpm run lint` |
| Format code | `pnpm run format` |
| Neo4j Browser | `open http://localhost:7474` |
| API Docs | `open http://localhost:8000/docs` |
| Grafana Dashboards | `open http://localhost:3001` |

---

**Questions?** Check the documentation or open an issue.

**Ready to code?** Start with Phase 2 - Skill Extraction in the next module!
