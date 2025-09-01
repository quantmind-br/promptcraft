# Frontend Services Layer

### API Client Setup
```typescript
import { QueryClient } from '@tanstack/react-query'

class ApiClient {
  private baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  private token: string | null = null
  
  constructor() {
    // Initialize token from localStorage on client side
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token')
    }
  }
  
  setAuthToken(token: string) {
    this.token = token
    localStorage.setItem('auth_token', token)
  }
  
  clearAuthToken() {
    this.token = null
    localStorage.removeItem('auth_token')
  }
  
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }
    
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    })
    
    if (!response.ok) {
      throw new ApiError(response.status, await response.text())
    }
    
    return response.json()
  }
  
  // Template operations
  async getTemplates(filters?: TemplateFilters): Promise<Template[]> {
    const params = new URLSearchParams(filters as any)
    return this.request<Template[]>(`/templates?${params}`)
  }
  
  async createTemplate(data: TemplateCreateInput): Promise<Template> {
    return this.request<Template>('/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }
  
  async updateTemplate(id: string, data: TemplateUpdateInput): Promise<Template> {
    return this.request<Template>(`/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }
  
  async deleteTemplate(id: string): Promise<void> {
    return this.request<void>(`/templates/${id}`, {
      method: 'DELETE',
    })
  }
}

export const apiClient = new ApiClient()

// Query client configuration
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 1,
    },
  },
})
```

### Service Example
```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { toast } from '@/components/ui/use-toast'

export function useTemplates(filters?: TemplateFilters) {
  return useQuery({
    queryKey: ['templates', filters],
    queryFn: () => apiClient.getTemplates(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useCreateTemplate() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: TemplateCreateInput) => apiClient.createTemplate(data),
    onSuccess: (newTemplate) => {
      // Update templates list
      queryClient.setQueryData(['templates'], (old: Template[] = []) => [
        newTemplate,
        ...old,
      ])
      
      toast({
        title: 'Template created',
        description: `Template "${newTemplate.name}" has been created successfully.`,
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to create template',
        description: error.message,
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TemplateUpdateInput }) =>
      apiClient.updateTemplate(id, data),
    onSuccess: (updatedTemplate) => {
      // Optimistically update templates list
      queryClient.setQueryData(['templates'], (old: Template[] = []) =>
        old.map(t => t.id === updatedTemplate.id ? updatedTemplate : t)
      )
      
      toast({
        title: 'Template updated',
        description: `Template "${updatedTemplate.name}" has been updated.`,
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to update template',
        description: error.message,
        variant: 'destructive',
      })
    },
  })
}
```
