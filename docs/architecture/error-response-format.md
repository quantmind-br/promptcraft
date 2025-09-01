# Error Response Format

```typescript
interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    requestId: string;
  };
}

// Example error responses
const validationError: ApiError = {
  error: {
    code: "VALIDATION_ERROR",
    message: "Template name must be unique",
    details: {
      field: "name",
      value: "duplicate-template",
      constraint: "unique"
    },
    timestamp: "2023-12-01T10:30:00Z",
    requestId: "req_abc123"
  }
}

const authError: ApiError = {
  error: {
    code: "AUTHENTICATION_FAILED",
    message: "Invalid or expired token",
    timestamp: "2023-12-01T10:30:00Z",
    requestId: "req_def456"
  }
}
```
