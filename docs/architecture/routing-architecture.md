# Routing Architecture

### Route Organization
```
app/
├── (auth)/
│   ├── login/
│   └── callback/
├── dashboard/
│   ├── templates/
│   │   ├── [id]/
│   │   └── new/
│   ├── teams/
│   │   ├── [slug]/
│   │   └── settings/
│   └── settings/
├── public/
│   └── templates/
└── api/
    ├── auth/
    ├── templates/
    └── sync/
```

### Protected Route Pattern
```typescript
'use client'

import { useAuth } from '@/hooks/use-auth'
import { redirect } from 'next/navigation'
import { useEffect } from 'react'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireTeam?: boolean
}

export function ProtectedRoute({ children, requireTeam = false }: ProtectedRouteProps) {
  const { user, isLoading, currentTeam } = useAuth()
  
  useEffect(() => {
    if (!isLoading && !user) {
      redirect('/login')
    }
    
    if (!isLoading && requireTeam && !currentTeam) {
      redirect('/dashboard/teams/join')
    }
  }, [user, isLoading, currentTeam, requireTeam])
  
  if (isLoading) {
    return <LoadingSpinner />
  }
  
  if (!user) {
    return null
  }
  
  if (requireTeam && !currentTeam) {
    return null
  }
  
  return <>{children}</>
}
```
