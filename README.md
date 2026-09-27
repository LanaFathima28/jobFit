# JobFit AI 🚀

**JobFit AI** is an intelligent, AI-powered candidate ranking and interview question generation platform. It leverages vector search and Large Language Models (LLMs) to match candidate resumes against job descriptions, calculate semantic fit scores, and automatically produce tailored interview questions to evaluate candidate skill gaps.

---

## 🌟 Key Features

- 🎯 **Vector-Based Candidate Matching**: Calculates semantic fit scores between resumes and job requirements using embeddings powered by PostgreSQL with `pgvector`.
- 📄 **Automated Resume Parsing**: Upload candidate resumes (PDF / DOCX) and automatically extract key skills, work experience, and educational background.
- 🤖 **AI-Generated Interview Questions**: Generates customized technical and behavioral interview questions tailored specifically to a candidate's profile and missing job requirements.
- ⚡ **Asynchronous Background Processing**: Offloads heavy tasks such as document embedding generation and LLM query generation using **Celery** and **Redis**.
- 📊 **Interactive Dashboard**: Modern UI built with **Next.js 14**, **Tailwind CSS**, and **TypeScript** to manage jobs, view ranked candidate matches, and review generated interview guides.

---

## 🛠️ Tech Stack

### **Backend**
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11)
- **Database**: PostgreSQL 16 with [`pgvector`](https://github.com/pgvector/pgvector) extension
- **ORM & Migrations**: SQLAlchemy & Alembic
- **Async Processing**: Celery with Redis broker
- **AI Integrations**: OpenAI API & Anthropic Claude

### **Frontend**
- **Framework**: [Next.js 14](https://nextjs.org/) (App Router, React 18, TypeScript)
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios

### **Infrastructure**
- **Containerization**: Docker & Docker Compose

---

## 📁 Project Structure

```text
jobFit/
├── docker-compose.yml       # Multi-container Docker configuration
├── .env.example             # Master environment configuration template
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints (jobs, candidates, matches, interviews)
│   │   ├── core/            # App configuration & security settings
│   │   ├── db/              # Database models, sessions, & migrations
│   │   ├── models/          # SQLAlchemy database models
│   │   ├── schemas/         # Pydantic data validation schemas
│   │   ├── services/        # Business logic (matching engine, LLM prompts, parsing)
│   │   └── worker/          # Celery async workers & tasks
│   ├── alembic/             # Database migration scripts
│   ├── Dockerfile           # Backend container build script
│   └── requirements.txt     # Python dependencies
└── frontend/                # Next.js 14 Web Application
    ├── src/
    │   ├── app/             # Next.js App Router pages (jobs, candidates, matches)
    │   ├── components/      # Reusable React UI components
    │   └── lib/             # API client & utility functions
    ├── Dockerfile           # Frontend container build script
    └── package.json         # Node.js dependencies
```

---

## 🚀 Quick Start with Docker (Recommended)

The simplest way to run JobFit AI with all services (PostgreSQL + pgvector, Redis, FastAPI, Celery, Next.js) is using Docker Compose.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### 1. Clone the repository & setup environment
```bash
git clone https://github.com/your-username/jobFit.git
cd jobFit

# Copy environment variables template
cp .env.example .env
```

### 2. Configure API Keys
Edit the `.env` file to add your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Launch with Docker Compose
```bash
docker compose up --build
```

### 4. Access the Applications
Once all containers complete initialization:
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 💻 Local Development (Without Docker)

If you prefer to run services individually for local development:

### 1. Database & Cache Prerequisites
Ensure you have PostgreSQL (with `pgvector` extension) and Redis running locally:
- PostgreSQL on port `5432`
- Redis on port `6379`

### 2. Backend Setup
```bash
cd backend

# Create & activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend dev server
uvicorn app.main:app --reload --port 8000
```

### 3. Celery Worker (Optional for Async Tasks)
In a separate terminal (with active venv):
```bash
cd backend
celery -A app.worker.celery_app worker --loglevel=info
```

### 4. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js dev server
npm run dev
```

---

## 📡 Core API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Application health & DB connection status |
| `POST` | `/api/v1/jobs/` | Create a new job description |
| `GET` | `/api/v1/jobs/` | List all job descriptions |
| `POST` | `/api/v1/candidates/upload` | Upload and parse candidate resume |
| `GET` | `/api/v1/candidates/` | List candidate profiles |
| `POST` | `/api/v1/matches/compute` | Run vector matching between job & candidates |
| `GET` | `/api/v1/matches/{job_id}` | Retrieve ranked candidate matches for a job |
| `POST` | `/api/v1/interviews/generate` | Generate tailored AI interview questions |

For complete interactive API documentation, visit `/docs` when the backend is running.

---

## 📜 License

This project is licensed under the MIT License.