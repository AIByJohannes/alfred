# A.L.F.R.E.D.

**A**utonomous **L**earning **F**ramework for **R**esourceful **E**xecution & **D**evelopment

![Next.js](https://img.shields.io/badge/-Next.js-000000?style=flat&logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Spring Boot](https://img.shields.io/badge/-Spring%20Boot-6DB33F?style=flat&logo=springboot&logoColor=white)
![Supabase](https://img.shields.io/badge/-Supabase-3ECF8E?style=flat&logo=supabase&logoColor=white)
![Redis](https://img.shields.io/badge/-Redis-DC382D?style=flat&logo=redis&logoColor=white)
![Python](https://img.shields.io/badge/-Python%203.12-3776AB?style=flat&logo=python&logoColor=white)
![Kotlin](https://img.shields.io/badge/-Kotlin-7F52FF?style=flat&logo=kotlin&logoColor=white)
![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)

A personal artificial intelligence platform with autonomous task execution capabilities.

## Monorepo Structure

This repository contains the complete Alfred platform as a monorepo:

```
alfred/
├── core/          # FastAPI AI Service (Python 3.12 + OpenRouter)
├── app/           # Spring Boot Backend (Kotlin) [Planned]
├── frontend/      # Next.js Frontend (TypeScript) [Planned]
└── docs/          # Architecture and documentation
```

## Services

### AI Service (`core/`)

**Status**: ✅ Active

FastAPI microservice providing LLM-powered AI capabilities through OpenRouter.

**Tech Stack**: Python 3.12, FastAPI, OpenAI SDK, OpenRouter

**Quick Start**:
```bash
cd core
poetry install
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
poetry run uvicorn main:app --reload
```

See [core/README.md](core/README.md) for detailed documentation.

### Backend Service (`app/`)

**Status**: 🚧 Planned

Kotlin Spring Boot microservice for user management, authentication, and API orchestration.

**Tech Stack**: Kotlin, Spring Boot 3.x, PostgreSQL (Supabase), JWT

See [app/README.md](app/README.md) for details.

### Frontend (`frontend/`)

**Status**: 🚧 Planned

Next.js web application for interacting with Alfred.

**Tech Stack**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui

See [frontend/README.md](frontend/README.md) for details.

## Architecture

Alfred follows a microservices architecture with three main components:

1. **AI Service (FastAPI)**: Handles LLM interactions and AI task execution
2. **Backend (Spring Boot)**: Manages users, authentication, and coordinates services
3. **Frontend (Next.js)**: Provides the user interface

See [docs/architecture.md](docs/architecture.md) for the complete architecture documentation.

## Getting Started

### Prerequisites

- **Python 3.12+** (for AI service)
- **Poetry** (Python dependency management)
- **Node.js 20+** (for frontend, when implemented)
- **Java 21+** (for backend, when implemented)
- **Docker** (optional, for containerized development)

### Local Development

#### Option 1: Run Services Individually

```bash
# AI Service
cd core
poetry install
cp .env.example .env
# Configure .env with your API keys
poetry run uvicorn main:app --reload --port 8000
```

#### Option 2: Docker Compose (Recommended)

```bash
# From repository root
docker-compose up
```

This will start all services with proper networking and dependencies.

## Environment Configuration

Each service requires its own environment configuration:

- **core/.env**: OpenRouter API keys and AI service settings
- **app/.env**: Database connection, JWT secrets (when implemented)
- **frontend/.env**: API endpoints, feature flags (when implemented)

See `.env.example` files in each service directory for required variables.

## API Documentation

When services are running:

- **AI Service**: http://localhost:8000/docs (Swagger UI)
- **Backend API**: http://localhost:8080/swagger-ui (when implemented)
- **Frontend**: http://localhost:3000 (when implemented)

## Client Applications

Alfred has companion applications for different platforms:

- [Android App](https://github.com/AIByJohannes/alfred-android/)
- [Desktop App](https://github.com/AIByJohannes/alfred-desktop)
- [CLI](https://github.com/AIByJohannes/alfred-cli/)

## Development Workflow

### Project Setup

```bash
# Clone repository
git clone https://github.com/AIByJohannes/alfred.git
cd alfred

# Set up AI service
cd core
poetry install
cp .env.example .env

# Return to root for other services
cd ..
```

### Running Tests

```bash
# AI Service
cd core
poetry run pytest

# Backend (when implemented)
cd app
./gradlew test

# Frontend (when implemented)
cd frontend
npm test
```

### Code Quality

Each service has its own linting and formatting tools:

- **Python (core/)**: black, ruff, mypy
- **Kotlin (app/)**: ktlint, detekt
- **TypeScript (frontend/)**: ESLint, Prettier

## Contributing

1. Create a feature branch from `main`
2. Make changes in the appropriate service directory
3. Ensure tests pass and code is formatted
4. Submit a pull request with a clear description

## License

See [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please open an issue on GitHub.
