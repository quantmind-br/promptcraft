# Frontend Error Handling

```typescript
import { toast } from '@/components/ui/use-toast'
import { ApiError } from '@/types/api'

class ErrorHandler {
  static handle(error: unknown, context?: string) {
    console.error(`Error in ${context}:`, error)
    
    if (this.isApiError(error)) {
      this.handleApiError(error)
    } else if (error instanceof Error) {
      this.handleGenericError(error)
    } else {
      this.handleUnknownError()
    }
  }
  
  private static isApiError(error: unknown): error is { response: { data: ApiError } } {
    return (
      typeof error === 'object' &&
      error !== null &&
      'response' in error &&
      typeof (error as any).response === 'object' &&
      'data' in (error as any).response
    )
  }
  
  private static handleApiError(error: { response: { data: ApiError } }) {
    const apiError = error.response.data.error
    
    toast({
      title: this.getErrorTitle(apiError.code),
      description: apiError.message,
      variant: 'destructive',
    })
    
    // Handle specific error types
    switch (apiError.code) {
      case 'AUTHENTICATION_FAILED':
        // Redirect to login
        window.location.href = '/login'
        break
      case 'RATE_LIMIT_EXCEEDED':
        // Show rate limit warning
        toast({
          title: 'Rate limit exceeded',
          description: 'Please wait before making more requests',
          variant: 'destructive',
        })
        break
      default:
        // Generic error handling
        break
    }
  }
  
  private static handleGenericError(error: Error) {
    toast({
      title: 'Something went wrong',
      description: error.message,
      variant: 'destructive',
    })
  }
  
  private static handleUnknownError() {
    toast({
      title: 'Unknown error',
      description: 'An unexpected error occurred',
      variant: 'destructive',
    })
  }
  
  private static getErrorTitle(code: string): string {
    const titles: Record<string, string> = {
      'VALIDATION_ERROR': 'Validation Failed',
      'AUTHENTICATION_FAILED': 'Authentication Error',
      'AUTHORIZATION_FAILED': 'Access Denied',
      'NOT_FOUND': 'Not Found',
      'RATE_LIMIT_EXCEEDED': 'Rate Limit Exceeded',
      'SERVER_ERROR': 'Server Error'
    }
    
    return titles[code] || 'Error'
  }
}

export { ErrorHandler }

// Usage in React components
export function useErrorHandler() {
  return (error: unknown, context?: string) => {
    ErrorHandler.handle(error, context)
  }
}

// Usage in React Query
export function useCreateTemplate() {
  const handleError = useErrorHandler()
  
  return useMutation({
    mutationFn: createTemplate,
    onError: (error) => handleError(error, 'Template Creation'),
  })
}
```
