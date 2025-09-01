# Authentication Service

**Responsibility:** Handles user authentication, authorization, and CLI token management

**Key Interfaces:**
- OAuth integration (GitHub)
- JWT token generation and validation
- CLI authentication via API tokens
- Session management

**Dependencies:** External OAuth providers, User database

**Technology Stack:** FastAPI OAuth2, JWT, GitHub OAuth, secure token storage
