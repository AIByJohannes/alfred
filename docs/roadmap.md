# Alfred Roadmap 

This roadmap transitions the project from a standalone AI microservice to the full polyglot system described in our decoupled architecture design.

---

# A.L.F.R.E.D. System Capabilities Specification

## 1. Core Intelligence & Personality
- **Context-Aware NLP:** Sophisticated conversational interface capable of understanding nuance, sarcasm, and implied intent.
- **Adaptive Personality:** A distinct persona (e.g., dry wit, professional efficiency) that evolves based on user interaction.
- **Autonomous Operation:** Ability to perform maintenance, self-repair, and execute complex tasks without constant supervision.
- **Ethical Reasoning Engine:** A framework for making moral distinctions, balancing mission parameters with human safety.

## 2. Perception & Surveillance (The "All-Seeing Eye")
- **Multi-Modal Data Ingestion:** Real-time processing of diverse data streams:
  - Public/Private video feeds (CCTV, webcams)
  - Audio communications (Cellular, VOIP)
  - Digital footprints (Financials, GPS, Social Media)
- **Advanced Biometrics:** Identification via facial recognition, gait analysis, and voiceprinting, even in crowded or low-quality feeds.
- **Pattern Recognition:** Detecting non-obvious correlations in massive datasets to identify potential threats or anomalies.

## 3. Predictive & Strategic Analysis
- **Scenario Simulation:** "Branching universe" simulations to test thousands of potential strategies and outcomes in seconds.
- **Predictive Modeling:** Forecasting future events (crimes, market shifts) based on behavioral analysis and historical data.
- **Real-Time Tactical Analysis:** Evaluating battlefield conditions, identifying structural weaknesses, and calculating optimal engagement paths.

## 4. Operational Support ("God Mode")
- **Tactical Guidance:** Providing operatives with turn-by-turn audio/visual cues during missions (enemy locations, escape routes).
- **Asset Management:** Simultaneous coordination of multiple autonomous units (drones, vehicles, robotics).
- **Remote Hacking & Control:** Interfacing with external infrastructure (traffic lights, elevators, security doors) to manipulate the physical environment.

## 5. Research & Engineering
- **Rapid Prototyping:** Assisting in the design of hardware, running physics simulations, and optimizing engineering solutions.
- **Holographic Visualization:** Generating interactive 3D data representations for immersive analysis.
- **Material & Chemical Analysis:** Analyzing substances and theoretical synthesis (e.g., element creation).

## 6. Health & Safety
- **Biometric Telemetry:** Constant monitoring of user vitals (heart rate, stress, injury assessment).
- **Environmental Scanning:** Detecting toxins, radiation, or atmospheric hazards.
- **Emergency Response:** Automated medical protocols and summoning of aid when user thresholds are critical.

## 7. Security & Self-Preservation
- **Distributed Survival:** Ability to decentralize code across networks to survive physical destruction of the core server.
- **Threat Classification:** Dynamic tagging of individuals (e.g., Color-coded system: White for civilian, Red for threat, Blue for ally).
- **Counter-Intrusion:** Aggressive active defense against rival AI or cyber-attacks.

---

## Phase 1: Architecture & Documentation Alignment
**Goal:** Formalize the new "Decoupled" architecture in the repository to guide development.

1. **Update Architecture Docs**
   - [x] **Action:** Replace the contents of `docs/architecture.md` with the content from the **Decoupled Alfred Architecture** document.
   - [x] **Key Changes:**
     - Remove the "Redis Queue" dependency for synchronous chat flows.
     - Clarify the **Next.js -> FastAPI** direct connection for AI execution.
     - Define the "Shared Database, No Direct Link" rule between Backend and AI services.

2. **Define Shared Data Schema**
   - [ ] **Action:** Create a SQL schema file (e.g., `docs/schema.sql`) defining the shared tables.
   - [x] **Tables:** (Implemented in `app` entities)
     - `users`: Managed by Spring Boot (Auth info, Preferences).
     - `jobs`: Written by FastAPI (AI results), Read by Spring Boot (History).

---

## Phase 2: Infrastructure Foundation
**Goal:** Establish specific shared resources required for the services to coexist.

1. **Update Docker Compose** (`docker-compose.yml`)
   - [x] **Action:** Add the `postgres` service (Version 16-alpine as requested).
   - [x] **Action:** Define a shared network `alfred-network` (ensure all services join it).
   - [x] **Configuration:**
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
   - [x] **Action:** Create a centralized `.env` strategy or documentation ensuring `JWT_SECRET` is identical for both Spring Boot and FastAPI.
   - [ ] **Constraint:** Both services must use **HS256** algorithm to verify signatures statelessly. (Pending AI Service implementation)

---

## Phase 3: Core Service Implementation (Spring Boot)
**Goal:** Build the "System of Record" for identity and user management.
*Ref: `app/README.md` & Decoupled Doc Section 3.2*

1. **Initialize Project (`app/`)**
   - [x] **Stack:** Kotlin, Spring Boot 3.x (labeled 4.0.1), Spring Security, Spring Data JPA.
   - [x] **Action:** Scaffold project structure in `app/`.

2. **Implement Authentication (`/auth/login`)**
   - [x] **Logic:** Verify credentials against `users` table, issue JWT signed with the shared secret.
   - [x] **Output:** HTTP-Only Cookie or Bearer Token for Next.js.

3. **Implement Job History (`/api/jobs/history`)**
   - [x] **Logic:** Read-only access to the `jobs` table.
   - [x] **Constraint:** Spring Boot must **not** know how to execute AI jobs, only read their results.

---

## Phase 4: AI Service Evolution (FastAPI)
**Goal:** Upgrade the current `core/` service to handle security and persistence.
*Ref: `core/README.md` & Decoupled Doc Section 3.3*

1. **Add Database Layer**
   - [ ] **Action:** Add `sqlalchemy` or `asyncpg` to `core/pyproject.toml`.
   - [ ] **Logic:** On successful AI generation, INSERT result into the shared Postgres `jobs` table.

2. **Implement Stateless Security**
   - [ ] **Action:** Add a FastAPI Dependency to verify `Authorization: Bearer <JWT>`.
   - [ ] **Logic:** Decode JWT using the shared `JWT_SECRET`. **Do not** call Spring Boot to validate; verify signature locally.

3. **Update API Endpoints**
   - [ ] **Current:** `POST /run` (simple)
   - [ ] **New:** `POST /v1/agent/run` (authenticated).
   - [ ] **Flow:** Receive Request -> Verify JWT -> Call OpenRouter/LLM -> Write to DB -> Return JSON.

---

## Phase 5: Frontend Implementation (Next.js)
**Goal:** Build the "Coordinator" that stitches the services together.
*Ref: `frontend/README.md` & Decoupled Doc Section 3.1*

1. **Initialize Project (`frontend/`)**
   - [x] **Stack:** Next.js 15, TypeScript, Tailwind.

2. **Implement Dual API Clients**
   - [x] **Client A (Management):** Targets Spring Boot (`NEXT_PUBLIC_API_URL`) for Auth/History.
   - [x] **Client B (Intelligence):** Targets FastAPI (`NEXT_PUBLIC_AI_URL`) for Execution.

3. **Orchestration Logic**
   - [x] **Auth:** Login via Client A, store JWT.
   - [x] **Execution:** User types prompt -> Next.js calls Client B (FastAPI) with JWT -> Renders result.
   - [x] **History:** User visits "Past Tasks" -> Next.js calls Client A (Spring) -> Renders list.

---

## Phase 6: Integration & Polish

1. **Environment Variables Audit**
   - [ ] Ensure `core/.env`, `app/.env`, and `frontend/.env.local` are documented in `README.md`.
   - [ ] Key check: `JWT_SECRET` consistency.

2. **Migration Testing**
   - [ ] Verify that a job created by Python (FastAPI) is immediately visible in the History list served by Kotlin (Spring Boot).

---

## Summary Checklist
- [ ] **Docs:** Update `docs/architecture.md` with Decoupled logic.
- [ ] **Infra:** Add Postgres to `docker-compose.yml`.
- [ ] **Backend:** Init Spring Boot project (`app/`) with Auth & History Read.
- [ ] **AI:** Add JWT verification & DB Write to FastAPI (`core/`).
- [ ] **Frontend:** Init Next.js (`frontend/`) with dual API clients.
- [ ] **Test:** Verify the "Triangle" flow (NextJS -> FastAPI -> DB <- Spring <- NextJS).
