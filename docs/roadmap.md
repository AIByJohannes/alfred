# Alfred Roadmap 

This roadmap transitions the project from a standalone AI microservice to the full polyglot system described in our decoupled architecture design.

## Phase 1: Architecture & Documentation Alignment
**Goal:** Formalize the new "Decoupled" architecture in the repository to guide development.

1. **Update Architecture Docs**
   - **Action:** Replace the contents of `docs/architecture.md` with the content from the **Decoupled Alfred Architecture** document.
   - **Key Changes:**
     - Remove the "Redis Queue" dependency for synchronous chat flows.
     - Clarify the **Next.js -> FastAPI** direct connection for AI execution.
     - Define the "Shared Database, No Direct Link" rule between Backend and AI services.

2. **Define Shared Data Schema**
   - **Action:** Create a SQL schema file (e.g., `docs/schema.sql`) defining the shared tables.
   - **Tables:**
     - `users`: Managed by Spring Boot (Auth info, Preferences).
     - `jobs`: Written by FastAPI (AI results), Read by Spring Boot (History).

---

## Phase 2: Infrastructure Foundation
**Goal:** Establish specific shared resources required for the services to coexist.

1. **Update Docker Compose** (`docker-compose.yml`)
   - **Action:** Add the `postgres` service (Version 16-alpine as requested).
   - **Action:** Define a shared network `alfred-network` (ensure all services join it).
   - **Configuration:**
     ```yaml
     services:
       postgres:
         image: postgres:16-alpine
         environment:
           POSTGRES_DB: alfred
           POSTGRES_USER: user
           POSTGRES_PASSWORD: pass
     ```

2. **Security Configuration (Shared Secrets)**
   - **Action:** Create a centralized `.env` strategy or documentation ensuring `JWT_SECRET` is identical for both Spring Boot and FastAPI.
   - **Constraint:** Both services must use **HS256** algorithm to verify signatures statelessly.

---

## Phase 3: Core Service Implementation (Spring Boot)
**Goal:** Build the "System of Record" for identity and user management.
*Ref: `app/README.md` & Decoupled Doc Section 3.2*

1. **Initialize Project (`app/`)**
   - **Stack:** Kotlin, Spring Boot 3.x, Spring Security, Spring Data JPA.
   - **Action:** Scaffold project structure in `app/`.

2. **Implement Authentication (`/auth/login`)**
   - **Logic:** Verify credentials against `users` table, issue JWT signed with the shared secret.
   - **Output:** HTTP-Only Cookie or Bearer Token for Next.js.

3. **Implement Job History (`/api/jobs/history`)**
   - **Logic:** Read-only access to the `jobs` table.
   - **Constraint:** Spring Boot must **not** know how to execute AI jobs, only read their results.

---

## Phase 4: AI Service Evolution (FastAPI)
**Goal:** Upgrade the current `core/` service to handle security and persistence.
*Ref: `core/README.md` & Decoupled Doc Section 3.3*

1. **Add Database Layer**
   - **Action:** Add `sqlalchemy` or `asyncpg` to `core/pyproject.toml`.
   - **Logic:** On successful AI generation, INSERT result into the shared Postgres `jobs` table.

2. **Implement Stateless Security**
   - **Action:** Add a FastAPI Dependency to verify `Authorization: Bearer <JWT>`.
   - **Logic:** Decode JWT using the shared `JWT_SECRET`. **Do not** call Spring Boot to validate; verify signature locally.

3. **Update API Endpoints**
   - **Current:** `POST /run` (simple)
   - **New:** `POST /v1/agent/run` (authenticated).
   - **Flow:** Receive Request -> Verify JWT -> Call OpenRouter/LLM -> Write to DB -> Return JSON.

---

## Phase 5: Frontend Implementation (Next.js)
**Goal:** Build the "Coordinator" that stitches the services together.
*Ref: `frontend/README.md` & Decoupled Doc Section 3.1*

1. **Initialize Project (`frontend/`)**
   - **Stack:** Next.js 15, TypeScript, Tailwind.

2. **Implement Dual API Clients**
   - **Client A (Management):** Targets Spring Boot (`NEXT_PUBLIC_API_URL`) for Auth/History.
   - **Client B (Intelligence):** Targets FastAPI (`NEXT_PUBLIC_AI_URL`) for Execution.

3. **Orchestration Logic**
   - **Auth:** Login via Client A, store JWT.
   - **Execution:** User types prompt -> Next.js calls Client B (FastAPI) with JWT -> Renders result.
   - **History:** User visits "Past Tasks" -> Next.js calls Client A (Spring) -> Renders list.

---

## Phase 6: Integration & Polish

1. **Environment Variables Audit**
   - Ensure `core/.env`, `app/.env`, and `frontend/.env.local` are documented in `README.md`.
   - Key check: `JWT_SECRET` consistency.

2. **Migration Testing**
   - Verify that a job created by Python (FastAPI) is immediately visible in the History list served by Kotlin (Spring Boot).

---

## Summary Checklist
- [ ] **Docs:** Update `docs/architecture.md` with Decoupled logic.
- [ ] **Infra:** Add Postgres to `docker-compose.yml`.
- [ ] **Backend:** Init Spring Boot project (`app/`) with Auth & History Read.
- [ ] **AI:** Add JWT verification & DB Write to FastAPI (`core/`).
- [ ] **Frontend:** Init Next.js (`frontend/`) with dual API clients.
- [ ] **Test:** Verify the "Triangle" flow (NextJS -> FastAPI -> DB <- Spring <- NextJS).
