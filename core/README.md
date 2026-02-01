# Alfred AI Service

FastAPI microservice providing LLM-powered AI capabilities for the Alfred platform.

## Overview

This service is the AI engine of Alfred, handling all LLM interactions through OpenRouter. It exposes a REST API for running prompts and executing AI-powered tasks.

## Technology Stack

- **Python**: 3.12+
- **Framework**: FastAPI
- **LLM Provider**: OpenRouter (supporting multiple models)
- **HTTP Client**: OpenAI SDK
- **Server**: Uvicorn with ASGI

## Features

- **LLM Integration**: OpenRouter API support for multiple LLM providers
- **REST API**: Simple endpoints for prompt execution
- **Health Checks**: Monitoring endpoint for service status
- **Example Tasks**: Built-in Fibonacci example demonstrating capabilities

## Prerequisites

- Python 3.12 or higher
- uv (for dependency management)
- OpenRouter API key ([Get one here](https://openrouter.ai/keys))

## Setup

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Dependencies

```bash
cd core
uv sync
```

### 3. Configure Environment

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```env
OPENROUTER_API_KEY=your_actual_api_key_here
```

### 4. Run the Service

```bash
# Development mode with auto-reload
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at `http://localhost:8000`

## API Endpoints

### Health Check

```bash
GET /health
```

Returns the service status.

**Response:**
```json
{
  "status": "healthy",
  "service": "Alfred AI Service"
}
```

### Run Prompt

```bash
POST /run
Content-Type: application/json

{
  "prompt": "Explain quantum computing in simple terms"
}
```

**Response:**
```json
{
  "result": "Quantum computing is...",
  "status": "success"
}
```

### Fibonacci Example

```bash
GET /fibonacci?n=10
```

Returns the nth Fibonacci number using AI.

## Project Structure

```
core/
├── llm/
│   └── __init__.py          # LLMEngine implementation
├── prompts/
│   └── __init__.py          # Prompt templates library
├── main.py                  # FastAPI application
├── models.py                # Pydantic request/response models
├── pyproject.toml           # Project dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

## Development

### Run Tests

```bash
uv run pytest
```

### Code Formatting

```bash
# Format with black
uv run black .

# Lint with ruff
uv run ruff check .
```

### Type Checking

```bash
uv run mypy .
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `OPENROUTER_API_KEY`: Your OpenRouter API key (required)
- `OPENROUTER_MODEL`: LLM model to use (default: openai/gpt-4o-mini)
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

## API Documentation

Interactive API documentation is available when the service is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Deployment

### Docker

Build and run with Docker:

```bash
docker build -t alfred-ai-service .
docker run -p 8000:8000 --env-file .env alfred-ai-service
```

### Docker Compose

From the repository root:

```bash
docker-compose up ai-service
```

## Architecture

This service is part of the Alfred monorepo architecture:

- **core/** (this service): FastAPI AI microservice
- **app/**: Kotlin Spring Boot backend
- **frontend/**: Next.js frontend

See `../docs/architecture.md` for the complete system architecture.

## Current Status

The service currently implements the basic LLM execution layer.
Pending implementation (see `../docs/roadmap.md`):
- [ ] Database integration (writing results to Postgres)
- [ ] Stateless Security (JWT verification)

## Contributing

When making changes:

1. Ensure all tests pass: `uv run pytest`
2. Format code: `uv run black .`
3. Check types: `uv run mypy .`
4. Update this README if adding new features

## License

See the LICENSE file in the repository root.
