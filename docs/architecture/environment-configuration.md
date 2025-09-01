# Environment Configuration

### Required Environment Variables

```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_GITHUB_CLIENT_ID=your_github_client_id

# Backend (.env)
DATABASE_URL=postgresql://user:password@localhost:5432/promptcraft
REDIS_URL=redis://localhost:6379
SECRET_KEY=your_secret_key_here
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
JWT_SECRET_KEY=your_jwt_secret_here
CLI_TOKEN_SECRET=your_cli_token_secret

# Shared
NODE_ENV=development
LOG_LEVEL=debug
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```
