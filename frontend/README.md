# Alfred Frontend (Next.js)

The central coordinator and UI for the Alfred platform.

## Technology Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **API Communication**: Fetch API with Dual Clients (Spring Boot & FastAPI)

## Architecture Role

As defined in `docs/architecture.md`, the frontend acts as the orchestrator:

1.  **Identity**: Communicates with the Spring Boot `app/` service for authentication and retrieving historical job data.
2.  **Intelligence**: Directly calls the FastAPI `core/` service to execute AI agents.
3.  **Security**: Manages and attaches JWT tokens to requests for both services.

## Development Setup

### 1. Environment Variables
Create a `frontend/.env.local` file:
```env
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_AI_URL=http://localhost:8000
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Run Development Server
```bash
npm run dev
```

## Directory Structure

- `app/`: Next.js App Router pages and layouts.
- `lib/api/`: Dual API clients for backend and AI services.
- `public/`: Static assets.