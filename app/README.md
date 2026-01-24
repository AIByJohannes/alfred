# Alfred Backend Service (Kotlin Spring Boot)

The Spring Boot backend microservice that provides authentication and core API functionality for Alfred.

## Technology Stack

- **Framework**: Spring Boot 4.0.1
- **Language**: Kotlin 2.2.21
- **Build Tool**: Gradle 9.2.1 with Kotlin DSL
- **Database**: PostgreSQL
- **Authentication**: JWT tokens (JJWT 0.13.0)
- **Security**: Spring Security 7
- **Java Version**: 21

## Features

### Implemented
- JWT-based authentication with HS256 algorithm
- User registration and login endpoints
- BCrypt password hashing
- Stateless session management
- Global exception handling
- Request validation

### Upcoming
- User profile management
- Integration with AI service (FastAPI in `core/`)
- Role-based access control
- API documentation with OpenAPI/Swagger

## Prerequisites

- Java 21 (OpenJDK)
- PostgreSQL database
- Environment variables configured (see below)

## Environment Variables

Create a `.env` file or configure the following environment variables:

```bash
# Database Configuration
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/alfred
SPRING_DATASOURCE_USERNAME=postgres
SPRING_DATASOURCE_PASSWORD=yourpassword

# JWT Configuration
JWT_SECRET=your-secret-key-at-least-256-bits-long-for-hs256-algorithm

# JPA/Hibernate
SPRING_JPA_HIBERNATE_DDL_AUTO=update  # Use 'validate' in production
```

**Important**: The `JWT_SECRET` must be at least 256 bits (32 characters) for HS256 and should be shared with the FastAPI service for token validation.

## Development Setup

### 1. Configure Java Home

If you encounter Java toolchain issues, create `gradle.properties`:

```properties
org.gradle.java.home=/usr/lib/jvm/java-21-openjdk-amd64
```

### 2. Start PostgreSQL Database

Using Docker Compose from the project root:

```bash
docker-compose up -d postgres
```

Or manually:

```bash
docker run -d \
  --name alfred-postgres \
  -e POSTGRES_DB=alfred \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  postgres:15
```

### 3. Build the Application

```bash
./gradlew build
```

To skip tests during build:

```bash
./gradlew build -x test
```

### 4. Run the Application

```bash
./gradlew bootRun
```

The service will start on `http://localhost:8080`

## API Endpoints

### Authentication

#### Register a New User

```bash
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

# Response (201 Created)
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "expiresIn": 86400
}
```

#### Login

```bash
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

# Response (200 OK)
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userId": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "expiresIn": 86400
}
```

### Using the JWT Token

For authenticated requests, include the token in the Authorization header:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Testing

### Manual Testing with curl

```bash
# Register a user
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Verify JWT token at https://jwt.io
```

### Run Unit Tests

```bash
./gradlew test
```

## JWT Token Structure

The JWT tokens are signed with HS256 and contain:

```json
{
  "sub": "<user-uuid>",
  "email": "<user-email>",
  "iss": "alfred-backend",
  "iat": <timestamp>,
  "exp": <timestamp>
}
```

- **Expiration**: 24 hours (86400000ms)
- **Algorithm**: HS256
- **Issuer**: alfred-backend

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## Directory Structure

```
app/
├── src/
│   ├── main/
│   │   ├── kotlin/com/alfred/app/
│   │   │   ├── config/          # Configuration classes
│   │   │   │   ├── JwtConfig.kt
│   │   │   │   └── SecurityConfig.kt
│   │   │   ├── controller/      # REST controllers
│   │   │   │   └── AuthController.kt
│   │   │   ├── dto/             # Data Transfer Objects
│   │   │   │   ├── AuthResponse.kt
│   │   │   │   ├── LoginRequest.kt
│   │   │   │   └── RegisterRequest.kt
│   │   │   ├── entity/          # JPA entities
│   │   │   │   └── User.kt
│   │   │   ├── exception/       # Exception handlers
│   │   │   │   └── AuthExceptionHandler.kt
│   │   │   ├── filter/          # Security filters
│   │   │   │   └── JwtAuthenticationFilter.kt
│   │   │   ├── repository/      # Data repositories
│   │   │   │   └── UserRepository.kt
│   │   │   ├── service/         # Business logic
│   │   │   │   ├── AuthService.kt
│   │   │   │   ├── CustomUserDetailsService.kt
│   │   │   │   └── JwtService.kt
│   │   │   └── AlfredBackendApplication.kt
│   │   └── resources/
│   │       └── application.properties
│   └── test/
├── build.gradle.kts
├── gradle.properties
└── README.md
```

## Security Considerations

- Passwords are hashed using BCrypt
- JWT tokens expire after 24 hours
- CSRF protection is disabled for stateless API
- All endpoints except `/auth/**` require authentication
- Session management is stateless

## Troubleshooting

### Java Toolchain Issues

If you see "Cannot find a Java installation", ensure:
1. Java 21 is installed: `java -version`
2. `JAVA_HOME` is set or configured in `gradle.properties`

### Database Connection Issues

- Verify PostgreSQL is running: `docker ps`
- Check environment variables are set correctly
- Ensure database exists: `psql -U postgres -c "\l"`

### Build Failures

Clean and rebuild:
```bash
./gradlew clean build
```

## Related Documentation

- [Spring Boot Documentation](../docs/spring_boot.md)
- [Architecture Overview](../README.md)
- [FastAPI Core Service](../core/README.md)
