# Alfred - Agent Context & Instructions

This file provides context, guidelines, and instructions for AI agents working on the Alfred project.

## 1. Project Overview
**Alfred** is a polyglot microservices system for AI-driven task execution.
- **Architecture**: Decoupled, Frontend-Driven.
- **Core Principle**: Separation of Concerns between "System of Record" (Backend) and "Intelligence Engine" (AI Service), connected via a shared database and orchestrated by the Frontend.

## 2. Directory Structure & Tech Stack

### Root
- **`docker-compose.yml`**: Infrastructure orchestration (Postgres, etc.).
- **`docs/`**: Architecture and roadmap documentation.

### `frontend/` (Next.js App)
*Status: Active*
- **Framework**: Next.js 16 (App Router).
- **Language**: TypeScript.
- **Styling**: Tailwind CSS 4.
- **Role**: UI, Auth flow handling, and orchestration of service calls.

### `app/` (Backend Service)
*Status: Active*
- **Framework**: Spring Boot 4.x.
- **Language**: Kotlin.
- **Role**: Identity Provider (Auth), User Management, Job History (Read-Only).
- **Database Access**: JPA / Hibernate.

### `core/` (AI Service)
*Status: Active*
- **Framework**: FastAPI.
- **Language**: Python 3.12.
- **Dependency Manager**: uv.
- **Role**: AI execution, LLM integration, Job creation (Write-Only).
- **Tools**: `ruff` (linting), `black` (formatting), `pytest` (testing).

### `database/`
- **`init.sql`**: Initial database schema (Users, Jobs).

## 3. Architecture Guidelines

### Communication
- **No Direct Service-to-Service Calls**: `app` (Spring Boot) and `core` (FastAPI) do not communicate directly.
- **Shared Database**: Both services connect to the same Postgres instance.
    - `core` WRITES results to `jobs` table.
    - `app` READS history from `jobs` table.

### Security
- **Authentication**: Stateless JWT (HS256).
- **Shared Secret**: `JWT_SECRET` must be identical across `app`, `core`, and `frontend` environments.
- **Flow**:
    1.  User logs in via `frontend` -> `app`.
    2.  `app` issues JWT.
    3.  `frontend` sends JWT to `core` for AI requests.
    4.  `core` verifies JWT signature locally (no call to `app`).

## 4. Development Workflow

### Setup (Typical)
1.  **Infrastructure**: `docker-compose up -d` (starts Postgres).
2.  **AI Service (`core/`)**:
    ```bash
    cd core
    uv sync
    uv run uvicorn main:app --reload
    ```
3.  **Backend (`app/`)**:
    ```bash
    cd app
    ./gradlew bootRun
    ```
4.  **Frontend (`frontend/`)**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

### Testing
- **AI Service**: `cd core && uv run pytest`
- **Backend**: `cd app && ./gradlew test`
- **Frontend**: `cd frontend && npm run test`

### Linting & Formatting
- **Python**: `ruff check .` and `black .`

## 5. Coding Standards
- **General**: Follow existing patterns. Prefer small, atomic changes.
- **Python**: Type hints are mandatory. Follow PEP 8.
- **Kotlin**: Idiomatic Kotlin.
- **TypeScript**: Strong typing, functional components.
- **Documentation**: Update `README.md` in subdirectories if architecture changes.
