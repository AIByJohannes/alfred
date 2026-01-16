# A.L.F.R.E.D.

**A**utonomous **L**earning **F**ramework for **R**esourceful **E**xecution & **D**evelopment

![Next.js](https://img.shields.io/badge/-Next.js%2016-000000?style=flat&logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Spring Boot](https://img.shields.io/badge/-Spring%20Boot%204-6DB33F?style=flat&logo=springboot&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-336791?style=flat&logo=postgresql&logoColor=white)
![Python](https://img.shields.io/badge/-Python%203.12-3776AB?style=flat&logo=python&logoColor=white)
![Kotlin](https://img.shields.io/badge/-Kotlin-7F52FF?style=flat&logo=kotlin&logoColor=white)
![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)

A polyglot microservices system for AI-driven task execution.

## Architecture

Alfred follows a **Decoupled, Frontend-Driven Architecture**:

*   **Frontend (Next.js)**: The orchestrator. It connects to the Backend for management and directly to the AI Service for execution.
*   **Backend (Spring Boot)**: The "System of Record". Handles authentication, user management, and historical data.
*   **AI Service (FastAPI)**: The "Intelligence Engine". Runs LLM agents and writes results to the shared database.
*   **Database (PostgreSQL)**: Shared persistence layer.

See [docs/architecture.md](docs/architecture.md) for details.

## Monorepo Structure

```
alfred/
├── core/          # AI Service (FastAPI, Python 3.12)
├── app/           # Backend Service (Spring Boot 4, Kotlin)
├── frontend/      # UI Application (Next.js 16, TypeScript)
├── database/      # SQL Initialization scripts
├── docs/          # Architecture and roadmap
└── docker-compose.yml # Infrastructure orchestration
```

## Services

### 1. AI Service (`core/`)
**Status**: Active
- **Role**: Execute AI tasks, interact with LLMs (via OpenRouter).
- **Stack**: FastAPI, Python 3.12, Poetry.
- **Port**: `8000`

### 2. Backend Service (`app/`)
**Status**: Initialized
- **Role**: Identity Provider (Auth), User Management, History Read-API.
- **Stack**: Spring Boot 4, Kotlin, Java 21, Gradle.
- **Port**: `8080`

### 3. Frontend (`frontend/`)
**Status**: Initialized
- **Role**: User Interface, Orchestration.
- **Stack**: Next.js 16 (App Router), React 19, Tailwind CSS 4.
- **Port**: `3000`

## Getting Started

### Prerequisites
- **Docker & Docker Compose** (Recommended for infrastructure)
- **Java 21**
- **Node.js 20+**
- **Python 3.12+** & **Poetry**

### Quick Start

1.  **Start Infrastructure (Postgres)**
    ```bash
    docker-compose up -d
    ```

2.  **Run AI Service**
    ```bash
    cd core
    poetry install
    # Copy .env.example to .env and add API keys
    poetry run uvicorn main:app --reload
    ```

3.  **Run Backend**
    ```bash
    cd app
    ./gradlew bootRun
    ```

4.  **Run Frontend**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## Development Workflow

### Communication Flow
1.  **Auth**: Frontend -> Backend (Get JWT).
2.  **AI Task**: Frontend -> AI Service (with JWT).
3.  **Persistence**: AI Service -> Postgres (`jobs` table).
4.  **History**: Frontend -> Backend -> Postgres (`jobs` table).

### Environment Variables
Ensure all services share the same `JWT_SECRET` for stateless authentication to work.

## License
See [LICENSE](LICENSE) file.
