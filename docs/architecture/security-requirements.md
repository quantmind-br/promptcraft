# Security Requirements

**Frontend Security:**
- CSP Headers: `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';`
- XSS Prevention: React's built-in XSS protection + content sanitization for user templates
- Secure Storage: JWT tokens in httpOnly cookies, sensitive data never in localStorage

**Backend Security:**
- Input Validation: Pydantic schemas for all API inputs with strict validation
- Rate Limiting: 100 requests per minute per user for API endpoints
- CORS Policy: Restricted to frontend domains only

**Authentication Security:**
- Token Storage: JWT in httpOnly cookies, CLI tokens in secure local config
- Session Management: 24-hour JWT expiry with refresh token rotation
- Password Policy: OAuth-only authentication, no password storage
