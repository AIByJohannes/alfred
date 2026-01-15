# Alfred Frontend (Next.js)

This directory will contain the Next.js frontend application for Alfred.

## Planned Technology Stack

- **Framework**: Next.js 15+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **State Management**: React Context / Zustand
- **Authentication**: Supabase Auth integration

## Architecture Role

According to the architecture document, this frontend will:

- Provide the user interface for interacting with Alfred
- Communicate with the Spring Boot backend (`app/`)
- Handle user authentication flows
- Display AI-generated responses and task results
- Manage user sessions and preferences

## Development Setup

*Coming soon - service not yet implemented*

To get started with Next.js:

```bash
# Initialize Next.js application
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir

# Install dependencies
npm install

# Run development server
npm run dev
```

## Directory Structure

```
frontend/
├── app/              # Next.js app directory (App Router)
├── components/       # React components
├── lib/             # Utility functions and configurations
├── public/          # Static assets
├── package.json
└── README.md        # This file
```
