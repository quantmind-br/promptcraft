# GitHub OAuth API

- **Purpose:** User authentication and profile information
- **Documentation:** https://docs.github.com/en/developers/apps/building-oauth-apps
- **Base URL(s):** https://api.github.com
- **Authentication:** OAuth 2.0 Authorization Code flow
- **Rate Limits:** 5000 requests per hour for authenticated users

**Key Endpoints Used:**
- `POST /login/oauth/access_token` - Exchange authorization code for access token
- `GET /user` - Get authenticated user profile information

**Integration Notes:** Used for web authentication and CLI setup flow. CLI authentication uses generated API tokens for performance.
