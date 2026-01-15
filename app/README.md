# Alfred Core Service (Kotlin Spring Boot)

This directory will contain the Kotlin Spring Boot microservice that serves as the main backend API for Alfred.

## Planned Technology Stack

- **Framework**: Spring Boot 3.x
- **Language**: Kotlin
- **Build Tool**: Gradle with Kotlin DSL
- **Database**: PostgreSQL (via Supabase)
- **Authentication**: JWT tokens
- **API Documentation**: OpenAPI/Swagger

## Architecture Role

According to the architecture document, this service will:

- Handle user authentication and session management
- Manage user data and preferences
- Coordinate requests to the AI service (FastAPI in `core/`)
- Provide the main REST API for the frontend
- Integrate with Supabase for database and authentication

## Development Setup

*Coming soon - service not yet implemented*

## Directory Structure

```
app/
├── src/
│   ├── main/
│   │   ├── kotlin/
│   │   └── resources/
│   └── test/
├── build.gradle.kts
└── README.md (this file)
```
