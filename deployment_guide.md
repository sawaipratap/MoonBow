# MoonBow Remote Deployment & Setup Guide

This guide details the exact steps required to set up the MoonBow infrastructure (PostgreSQL, MinIO, and Python environment) on a fresh remote machine (e.g., AWS EC2, GCP Compute Engine, or a dedicated Ubuntu server) from scratch.

---

## 1. Prerequisites

Ensure your remote machine has the following installed:
- **Python 3.12+** (required for `pydantic-core` prebuilt wheels)
- **Docker & Docker Compose**
- **Git**

***

## 2. Infrastructure Setup (Dockerized)

Rather than running commands manually, use `docker-compose` to spin up the required backing services.

### A. Create `docker-compose.yml`
In the root of the MoonBow repository on the remote machine, create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: moonbow-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  minio:
    image: quay.io/minio/minio:latest
    container_name: moonbow-minio
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data
    restart: unless-stopped

volumes:
  pgdata:
  miniodata:
```

### B. Start the Services
Run the following command in the directory containing your `docker-compose.yml`:
```bash
docker-compose up -d
```

***

## 3. Database Initialization

Once the Postgres container is running, initialize the required schemas for Phase 1 and Phase 2.

Run this command on the remote server to pipe the DDL into the container:

```bash
docker exec -i moonbow-postgres psql -U postgres -d postgres <<'EOF'
CREATE TABLE IF NOT EXISTS syllabuses (
    course_code TEXT PRIMARY KEY,
    syllabus JSONB NOT NULL,
    phase_status TEXT NOT NULL,
    iteration_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refined_syllabuses (
    course_code TEXT PRIMARY KEY,
    syllabus JSONB NOT NULL,
    evaluation_results JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    course_code TEXT NOT NULL,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS course_outcomes (
    course_code TEXT PRIMARY KEY,
    outcomes JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lecture_plans (
    course_code TEXT PRIMARY KEY,
    plan JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ppt_content (
    course_code TEXT,
    lecture_number INTEGER,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (course_code, lecture_number)
);
EOF
```

***

## 4. Object Storage (MinIO) Initialization

The MinIO server handles all curriculum files, parsed PDFs, evaluator skills, and generated outputs.

1. **Access the MinIO UI:**
   Navigate in your browser to `http://<SERVER_IP>:9001`
   - **Username:** `minioadmin`
   - **Password:** `minioadmin`

2. **Create the Core Buckets:**
   Click "Create Bucket" and create the following exactly as named:
   - `curricula`
   - `skills`
   - `generated-content`

3. **Upload the Core Skills:**
   Go to the `skills` bucket. Upload all the `.md` files located locally in your `/skills/knowledge` directory.
   *(Essential files: `academic_level_calibrator.md`, `curriculum_parser_instructions.md`, etc.)*

4. **Upload a Target Curriculum:**
   Go to the `curricula` bucket. Upload the target curriculum file (e.g., `Linear Algebra.md` or a PDF) that you intend to process.

***

## 5. Python Environment Setup

Clone the MoonBow repository on the remote machine if you haven't already.

```bash
# Verify Python version (must be >= 3.12 for prebuilt wheels)
python3 --version

# Create and activate the virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the dependencies core to Phase 1 and Phase 2
pip install -r requirements.txt
```

***

## 6. Environment Configuration (`.env`)

Create a `.env` file in the root of the project with the following configuration. Replace `localhost` with the respective remote IP addresses if your Docker services are running on a different machine than your Python code.

```env
# Mode Selector (Forces MCPs to use DB/MinIO instead of local mocks)
DEPENDENCY_MODE=real

# LLM Configuration
LLM_BASE_URL=https://api.minimax.io/v1
LLM_API_KEY=your_minimax_api_key_here
LLM_MODEL_NAME=MiniMax-M2.7
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=190000
MAX_ITERATIONS=3

# PostgreSQL Connection
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_POOL_SIZE=5

# MinIO Connection
MINIO_ENDPOINT=http://127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
CURRICULUM_BUCKET=curricula
SKILLS_BUCKET=skills
OUTPUT_BUCKET=generated-content

# Reference Database (For Phase 2 Relevance Evaluator connections)
REFDB_HOST=127.0.0.1
REFDB_PORT=5432
REFDB_NAME=moonbow_refdb
REFDB_USER=moonbow_user
REFDB_PASSWORD=moonbow123
```

***

## 7. Running the Pipeline

You are now ready to run the architecture end-to-end.

### Run Phase 1
Phase 1 reads the raw curriculum from MinIO, invokes the LangGraph LLM workflow to expand and critique the curriculum, and writes the JSONB graph object directly to PostgreSQL.

```bash
# Make sure the venv is active
source venv/bin/activate

# Run Phase 1 against a file currently living in your MinIO 'curricula' bucket
python -m phase1.run_phase1 "Linear Algebra.md"
```

### Run Phase 2
Phase 2 reads the expanded syllabus directly out of PostgreSQL, hits MinIO for the specific evaluation rubric skills, invokes 4 parallel intelligent evaluators (Level, Sequence, Hours, Relevance), and compiles the pass/fail feedback.

```bash
# Because Phase 1 uses heuristic course code extraction, verify the exact
# 'course_code' name it dumped into the DB. 
# Assuming it was "Linear Algebra":

python -m phase2.run_phase2 "Linear Algebra"
```
