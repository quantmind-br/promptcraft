# Critical Fullstack Rules

- **Type Sharing:** Always define types in packages/shared and import from both TypeScript and Python codebases
- **API Calls:** Never make direct HTTP calls from components - use the service layer with React Query
- **Environment Variables:** Access only through config objects, never process.env directly in components
- **Error Handling:** All API routes must use the standard error handler with proper HTTP status codes
- **State Updates:** Never mutate state directly - use Zustand actions or React state setters properly
- **Database Queries:** Always use repository pattern, never write raw SQL in service layer
- **CLI Performance:** CLI operations must complete in <150ms - use caching and optimize file operations
- **Authentication:** CLI and web must use the same user model but different token validation flows
- **Template Validation:** All template content must be validated for $ARGUMENTS syntax before storage
- **Real-time Updates:** WebSocket events must be handled gracefully with fallback to polling
