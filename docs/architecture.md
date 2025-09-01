# PromptCraft Fullstack Architecture Document

This document outlines the complete fullstack architecture for PromptCraft, including backend systems, frontend implementation, and their integration. It serves as the single source of truth for AI-driven development, ensuring consistency across the entire technology stack.

This unified approach combines what would traditionally be separate backend and frontend architecture documents, streamlining the development process for modern fullstack applications where these concerns are increasingly intertwined.

## Starter Template or Existing Project

**Current State:** Existing CLI tool implementation in Python with plans for web interface evolution

**Existing Components:**
- Python CLI application with click framework
- File-based template system (.promptcraft/commands/)
- Cross-platform clipboard integration via pyperclip
- Local template discovery and processing engine

**Architecture Strategy:** Hybrid approach maintaining existing CLI performance while adding web collaboration layer through API synchronization.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-09-01 | 1.0 | Initial full-stack architecture | Winston (Architect) |

# High Level Architecture

## Technical Summary

PromptCraft employs a hybrid full-stack architecture that preserves the high-performance CLI tool while adding collaborative web capabilities. The system uses FastAPI for the backend API with PostgreSQL for team data, while maintaining file-system based operations for CLI performance. The frontend utilizes Next.js with React for optimal developer experience, featuring real-time synchronization between CLI and web interfaces through WebSocket connections and API polling.

Key integration points include a unified authentication system using JWT tokens, bidirectional template synchronization, and a shared TypeScript interface layer. The infrastructure deploys on Vercel for the frontend with Railway for the backend API, ensuring sub-150ms CLI performance while enabling team collaboration features.

## Platform and Infrastructure Choice

**Platform:** Vercel + Railway
**Key Services:** Vercel Edge Functions, Railway PostgreSQL, Redis for caching, GitHub for authentication
**Deployment Host and Regions:** Global edge deployment via Vercel CDN, Railway US-West for API

**Rationale:** This combination provides optimal developer experience with zero-config deployments, automatic scaling, and excellent performance for both CLI sync operations and web interface. Railway offers superior database performance compared to serverless alternatives while maintaining cost efficiency.

## Repository Structure

**Structure:** Monorepo with workspace management
**Monorepo Tool:** npm workspaces with Turborepo for build optimization
**Package Organization:** Apps (cli, web, api) + shared packages (types, config, ui)

## High Level Architecture Diagram

```mermaid
graph TD
    A[Developer CLI] --> B[Local File System]
    A --> C[FastAPI Backend]
    
    D[Web Interface] --> C
    C --> E[PostgreSQL]
    C --> F[Redis Cache]
    C --> G[Authentication Service]
    
    H[Team Members] --> D
    H --> A
    
    I[External Services] --> C
    J[GitHub OAuth] --> G
    
    C --> K[WebSocket Server]
    D --> K
    A --> K
    
    L[CDN/Edge] --> D
    M[File Storage] --> C
```

## Architectural Patterns

- **Hybrid Architecture:** CLI-first with web collaboration layer - _Rationale:_ Preserves CLI performance while enabling team features
- **API-First Design:** RESTful APIs with WebSocket real-time sync - _Rationale:_ Ensures consistency between CLI and web interfaces
- **Component-Based UI:** React with TypeScript and Tailwind CSS - _Rationale:_ Developer-familiar stack with excellent TypeScript support
- **Repository Pattern:** Abstract data access for both file system and database - _Rationale:_ Enables flexible storage backends and testing
- **Event-Driven Sync:** WebSocket events for real-time template updates - _Rationale:_ Immediate synchronization between CLI and web users
- **Monorepo Pattern:** Shared types and utilities across CLI, API, and web - _Rationale:_ Ensures type safety and code reuse across the entire stack

# Tech Stack

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| Frontend Language | TypeScript | 5.0+ | Type-safe web development | Excellent developer experience and error prevention |
| Frontend Framework | Next.js | 14+ | React framework with SSR | Perfect for developer tools with great performance |
| UI Component Library | Shadcn/ui | Latest | Design system components | High-quality, customizable, developer-focused |
| State Management | Zustand | 4.0+ | Client state management | Lightweight, TypeScript-first, simple API |
| Backend Language | Python | 3.10+ | API and CLI development | Maintains existing CLI codebase compatibility |
| Backend Framework | FastAPI | 0.100+ | High-performance API | Excellent TypeScript integration and performance |
| API Style | REST + WebSocket | - | API communication | RESTful for CRUD, WebSocket for real-time sync |
| Database | PostgreSQL | 15+ | Primary data storage | Robust, well-supported, excellent JSON support |
| Cache | Redis | 7+ | Session and API caching | High-performance caching for API responses |
| File Storage | Local + S3 | - | Template storage | Hybrid local files + cloud backup |
| Authentication | JWT + OAuth | - | User authentication | Standard, secure, CLI-compatible |
| Frontend Testing | Vitest + RTL | Latest | Unit and component tests | Fast, modern testing with great DX |
| Backend Testing | Pytest | 7+ | API and CLI testing | Excellent Python testing framework |
| E2E Testing | Playwright | 1.40+ | End-to-end testing | Reliable, fast e2e tests |
| Build Tool | Vite | 5+ | Frontend build system | Lightning-fast builds and HMR |
| Bundler | Rollup | Latest | Code bundling | Vite's default bundler |
| IaC Tool | Railway Config | - | Infrastructure setup | Simple deployment configuration |
| CI/CD | GitHub Actions | - | Build and deployment | Integrated with repository |
| Monitoring | Sentry | Latest | Error tracking | Excellent error tracking and performance monitoring |
| Logging | Pino | Latest | Structured logging | High-performance structured logging |
| CSS Framework | Tailwind CSS | 3.0+ | Utility-first styling | Perfect for component libraries |

# Data Models

## Template

**Purpose:** Core entity representing a prompt template with metadata and content

**Key Attributes:**
- id: string - Unique identifier
- name: string - Command name (without extension)
- content: string - Template content with $ARGUMENTS placeholders
- description: string - Template description from first line
- owner_id: string - User who created the template
- team_id: string - Team ownership (optional)
- is_public: boolean - Public visibility flag
- created_at: datetime - Creation timestamp
- updated_at: datetime - Last modification timestamp
- usage_count: number - Number of times used
- tags: string[] - Categorization tags

### TypeScript Interface
```typescript
interface Template {
  id: string;
  name: string;
  content: string;
  description?: string;
  owner_id: string;
  team_id?: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  usage_count: number;
  tags: string[];
}
```

### Relationships
- Belongs to User (owner)
- Belongs to Team (optional)
- Has many TemplateVersions

## User

**Purpose:** User account with authentication and preferences

**Key Attributes:**
- id: string - Unique user identifier
- email: string - User email address
- name: string - Display name
- github_id: string - GitHub OAuth ID
- cli_token: string - API token for CLI authentication
- preferences: object - User preferences and settings
- created_at: datetime - Account creation
- last_active: datetime - Last activity timestamp

### TypeScript Interface
```typescript
interface User {
  id: string;
  email: string;
  name: string;
  github_id?: string;
  cli_token: string;
  preferences: UserPreferences;
  created_at: string;
  last_active: string;
}

interface UserPreferences {
  theme: 'light' | 'dark';
  default_team?: string;
  cli_sync_enabled: boolean;
}
```

### Relationships
- Has many Templates (owned)
- Belongs to many Teams (through TeamMember)
- Has many TemplateSyncEvents

## Team

**Purpose:** Team organization for template sharing and collaboration

**Key Attributes:**
- id: string - Unique team identifier
- name: string - Team display name
- slug: string - URL-safe team identifier
- owner_id: string - Team owner
- settings: object - Team configuration
- created_at: datetime - Team creation
- member_count: number - Current member count

### TypeScript Interface
```typescript
interface Team {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  settings: TeamSettings;
  created_at: string;
  member_count: number;
}

interface TeamSettings {
  public_templates: boolean;
  require_approval: boolean;
  sync_enabled: boolean;
}
```

### Relationships
- Belongs to User (owner)
- Has many Users (through TeamMember)
- Has many Templates

# API Specification

## REST API Specification

```yaml
openapi: 3.0.0
info:
  title: PromptCraft API
  version: 1.0.0
  description: REST API for PromptCraft template management and synchronization
servers:
  - url: https://api.promptcraft.dev
    description: Production API server

paths:
  /auth/login:
    post:
      summary: Authenticate user with GitHub OAuth
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                code:
                  type: string
                  description: GitHub OAuth authorization code
      responses:
        '200':
          description: Authentication successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  user:
                    $ref: '#/components/schemas/User'
  
  /templates:
    get:
      summary: List user templates
      parameters:
        - name: team_id
          in: query
          schema:
            type: string
        - name: public
          in: query
          schema:
            type: boolean
      responses:
        '200':
          description: List of templates
          content:
            application/json:
              schema:
                type: object
                properties:
                  templates:
                    type: array
                    items:
                      $ref: '#/components/schemas/Template'
    post:
      summary: Create new template
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TemplateCreate'
      responses:
        '201':
          description: Template created successfully
  
  /templates/{id}:
    get:
      summary: Get template by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Template details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Template'
    put:
      summary: Update template
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TemplateUpdate'
      responses:
        '200':
          description: Template updated successfully
    delete:
      summary: Delete template
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '204':
          description: Template deleted successfully

  /sync/cli:
    post:
      summary: Sync CLI templates with server
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                local_templates:
                  type: array
                  items:
                    $ref: '#/components/schemas/LocalTemplate'
      responses:
        '200':
          description: Sync result
          content:
            application/json:
              schema:
                type: object
                properties:
                  conflicts:
                    type: array
                    items:
                      $ref: '#/components/schemas/SyncConflict'
                  updates:
                    type: array
                    items:
                      $ref: '#/components/schemas/Template'

components:
  schemas:
    Template:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        content:
          type: string
        description:
          type: string
        owner_id:
          type: string
        team_id:
          type: string
        is_public:
          type: boolean
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        usage_count:
          type: integer
        tags:
          type: array
          items:
            type: string
    
    User:
      type: object
      properties:
        id:
          type: string
        email:
          type: string
        name:
          type: string
        github_id:
          type: string
        preferences:
          type: object
        created_at:
          type: string
          format: date-time
        last_active:
          type: string
          format: date-time

    TemplateCreate:
      type: object
      required:
        - name
        - content
      properties:
        name:
          type: string
        content:
          type: string
        description:
          type: string
        team_id:
          type: string
        is_public:
          type: boolean
        tags:
          type: array
          items:
            type: string

    TemplateUpdate:
      type: object
      properties:
        name:
          type: string
        content:
          type: string
        description:
          type: string
        is_public:
          type: boolean
        tags:
          type: array
          items:
            type: string

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []
```

# Components

## CLI Agent

**Responsibility:** Maintains existing CLI functionality while adding synchronization capabilities

**Key Interfaces:**
- Local file system operations
- Template discovery and processing
- API synchronization endpoints
- Clipboard integration

**Dependencies:** FastAPI backend for sync, local file system for templates

**Technology Stack:** Python 3.10+, click, pyperclip, httpx for API calls, asyncio for background sync

## Web Application

**Responsibility:** Provides web-based template management, team collaboration, and visual template editing

**Key Interfaces:**
- Template CRUD operations
- Real-time collaboration features
- Team management interface
- Authentication and user management

**Dependencies:** Backend API, Authentication service, WebSocket server

**Technology Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, Shadcn/ui components

## Backend API Service

**Responsibility:** Central API server handling authentication, data persistence, and synchronization logic

**Key Interfaces:**
- REST API endpoints
- WebSocket connections for real-time updates
- Authentication and authorization
- Database operations

**Dependencies:** PostgreSQL database, Redis cache, External OAuth providers

**Technology Stack:** FastAPI, SQLAlchemy, PostgreSQL, Redis, JWT tokens

## Authentication Service

**Responsibility:** Handles user authentication, authorization, and CLI token management

**Key Interfaces:**
- OAuth integration (GitHub)
- JWT token generation and validation
- CLI authentication via API tokens
- Session management

**Dependencies:** External OAuth providers, User database

**Technology Stack:** FastAPI OAuth2, JWT, GitHub OAuth, secure token storage

## Template Sync Engine

**Responsibility:** Manages bidirectional synchronization between CLI file system and web database

**Key Interfaces:**
- Conflict resolution algorithms
- Change detection and merging
- Real-time sync notifications
- Batch synchronization operations

**Dependencies:** File system operations, Database operations, WebSocket notifications

**Technology Stack:** Python asyncio, file system watchers, PostgreSQL, WebSocket server

## Component Diagrams

```mermaid
graph TB
    subgraph "Client Layer"
        A[CLI Application]
        B[Web Interface]
    end
    
    subgraph "API Layer"
        C[FastAPI Server]
        D[WebSocket Server]
        E[Auth Service]
    end
    
    subgraph "Business Layer"
        F[Template Service]
        G[User Service]
        H[Team Service]
        I[Sync Engine]
    end
    
    subgraph "Data Layer"
        J[PostgreSQL]
        K[Redis Cache]
        L[File System]
    end
    
    A --> C
    A --> D
    A --> L
    B --> C
    B --> D
    
    C --> E
    C --> F
    C --> G
    C --> H
    
    F --> I
    F --> J
    G --> J
    H --> J
    I --> L
    I --> K
    
    E --> J
    D --> K
```

# External APIs

## GitHub OAuth API

- **Purpose:** User authentication and profile information
- **Documentation:** https://docs.github.com/en/developers/apps/building-oauth-apps
- **Base URL(s):** https://api.github.com
- **Authentication:** OAuth 2.0 Authorization Code flow
- **Rate Limits:** 5000 requests per hour for authenticated users

**Key Endpoints Used:**
- `POST /login/oauth/access_token` - Exchange authorization code for access token
- `GET /user` - Get authenticated user profile information

**Integration Notes:** Used for web authentication and CLI setup flow. CLI authentication uses generated API tokens for performance.

# Core Workflows

```mermaid
sequenceDiagram
    participant CLI as CLI Client
    participant FS as File System
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant WS as WebSocket Server
    participant Web as Web Client

    Note over CLI,Web: Template Creation and Sync Flow
    
    CLI->>FS: Create local template
    CLI->>API: Sync request with local templates
    API->>DB: Check for conflicts
    DB-->>API: Return conflict status
    API->>WS: Broadcast template update
    WS->>Web: Real-time template notification
    API-->>CLI: Sync confirmation
    Web->>API: Fetch updated templates
    API->>DB: Query templates
    DB-->>API: Return templates
    API-->>Web: Template data

    Note over CLI,Web: Team Collaboration Flow
    
    Web->>API: Create team template
    API->>DB: Store template
    API->>WS: Broadcast to team members
    WS->>CLI: Notify CLI clients
    CLI->>API: Background sync check
    API->>DB: Get team updates
    DB-->>API: Return new templates
    API-->>CLI: Sync team templates
    CLI->>FS: Update local files
```

# Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    github_id VARCHAR(255) UNIQUE,
    cli_token VARCHAR(255) UNIQUE NOT NULL,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Teams table
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Team memberships
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

-- Templates table
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    is_public BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, owner_id, team_id)
);

-- Template versions for history
CREATE TABLE template_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES templates(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(template_id, version_number)
);

-- Sync events for CLI synchronization
CREATE TABLE sync_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    template_id UUID REFERENCES templates(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    sync_status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_templates_owner_team ON templates(owner_id, team_id);
CREATE INDEX idx_templates_name ON templates(name);
CREATE INDEX idx_templates_public ON templates(is_public) WHERE is_public = true;
CREATE INDEX idx_templates_tags ON templates USING GIN(tags);
CREATE INDEX idx_sync_events_user_status ON sync_events(user_id, sync_status);
CREATE INDEX idx_team_members_user ON team_members(user_id);
```

# Frontend Architecture

## Component Architecture

### Component Organization
```
src/
├── components/
│   ├── ui/                 # Shadcn/ui base components
│   ├── templates/         # Template-specific components
│   ├── teams/             # Team management components
│   ├── layout/            # Layout components
│   └── common/            # Shared components
├── pages/                 # Next.js pages
├── hooks/                 # Custom React hooks
├── lib/                   # Utility functions
├── stores/                # Zustand state stores
└── types/                 # TypeScript type definitions
```

### Component Template
```typescript
import { cn } from '@/lib/utils'
import { forwardRef } from 'react'

interface TemplateCardProps extends React.HTMLAttributes<HTMLDivElement> {
  template: Template
  onEdit?: () => void
  onDelete?: () => void
  variant?: 'default' | 'compact'
}

const TemplateCard = forwardRef<HTMLDivElement, TemplateCardProps>(
  ({ template, onEdit, onDelete, variant = 'default', className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border bg-card text-card-foreground shadow-sm',
          variant === 'compact' && 'p-3',
          variant === 'default' && 'p-6',
          className
        )}
        {...props}
      >
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="font-semibold leading-none">{template.name}</h3>
            {template.description && (
              <p className="text-sm text-muted-foreground">
                {template.description}
              </p>
            )}
          </div>
          <TemplateCardActions 
            onEdit={onEdit} 
            onDelete={onDelete}
          />
        </div>
        <TemplateCardFooter template={template} />
      </div>
    )
  }
)

TemplateCard.displayName = 'TemplateCard'

export { TemplateCard, type TemplateCardProps }
```

## State Management Architecture

### State Structure
```typescript
interface AppStore {
  // Authentication
  user: User | null
  isAuthenticated: boolean
  
  // Templates
  templates: Template[]
  selectedTemplate: Template | null
  templateFilters: TemplateFilters
  
  // Teams
  currentTeam: Team | null
  teams: Team[]
  
  // UI State
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  
  // Actions
  setUser: (user: User | null) => void
  setTemplates: (templates: Template[]) => void
  updateTemplate: (id: string, updates: Partial<Template>) => void
  setCurrentTeam: (team: Team | null) => void
  toggleSidebar: () => void
}

// Store implementation using Zustand
export const useAppStore = create<AppStore>((set, get) => ({
  user: null,
  isAuthenticated: false,
  templates: [],
  selectedTemplate: null,
  templateFilters: {},
  currentTeam: null,
  teams: [],
  sidebarOpen: true,
  theme: 'light',
  
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setTemplates: (templates) => set({ templates }),
  updateTemplate: (id, updates) => set((state) => ({
    templates: state.templates.map(t => 
      t.id === id ? { ...t, ...updates } : t
    )
  })),
  setCurrentTeam: (team) => set({ currentTeam: team }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen }))
}))
```

### State Management Patterns
- Single global store for application state
- Separate stores for different domains (auth, templates, teams)
- Optimistic updates for better UX
- Server state managed by React Query for caching

## Routing Architecture

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

## Frontend Services Layer

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

# Backend Architecture

## Service Architecture

### Function Organization
```
src/promptcraft_api/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── config.py          # Configuration management
│   ├── security.py        # Authentication and security
│   └── database.py        # Database connection and setup
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py    # Authentication endpoints
│   │   │   ├── templates.py # Template CRUD operations
│   │   │   ├── teams.py   # Team management
│   │   │   └── sync.py    # CLI synchronization
│   │   └── api.py         # API router aggregation
├── models/
│   ├── user.py            # User database models
│   ├── template.py        # Template database models
│   └── team.py            # Team database models
├── services/
│   ├── auth_service.py    # Authentication business logic
│   ├── template_service.py # Template operations
│   ├── sync_service.py    # Synchronization logic
│   └── notification_service.py # WebSocket notifications
└── utils/
    ├── dependencies.py    # FastAPI dependencies
    ├── exceptions.py      # Custom exceptions
    └── helpers.py         # Utility functions
```

### Function Template
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.template import Template
from ..schemas.template import TemplateCreate, TemplateResponse, TemplateUpdate
from ..services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])

@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    template_service: TemplateService = Depends()
):
    """Create a new template."""
    try:
        template = await template_service.create_template(
            db=db,
            user_id=current_user.id,
            template_data=template_data
        )
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )

@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    team_id: Optional[str] = None,
    public: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    template_service: TemplateService = Depends()
):
    """List user templates with optional filters."""
    templates = await template_service.list_user_templates(
        db=db,
        user_id=current_user.id,
        team_id=team_id,
        include_public=public,
        skip=skip,
        limit=limit
    )
    return templates

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    template_service: TemplateService = Depends()
):
    """Get template by ID."""
    template = await template_service.get_template_by_id(
        db=db,
        template_id=template_id,
        user_id=current_user.id
    )
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return template
```

## Database Architecture

### Schema Design
```sql
-- Core tables with optimized indexes
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    github_id VARCHAR(255) UNIQUE,
    cli_token VARCHAR(255) UNIQUE NOT NULL,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    is_public BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_template_per_scope UNIQUE(name, owner_id, COALESCE(team_id, '00000000-0000-0000-0000-000000000000'))
);

-- Performance indexes
CREATE INDEX idx_templates_owner_team ON templates(owner_id, team_id);
CREATE INDEX idx_templates_public_search ON templates(is_public, name, tags) WHERE is_public = true;
CREATE INDEX idx_templates_team_search ON templates(team_id, name) WHERE team_id IS NOT NULL;
CREATE INDEX idx_users_cli_token ON users(cli_token);
CREATE INDEX idx_teams_slug ON teams(slug);
```

### Data Access Layer
```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from uuid import UUID

from ..models.template import Template
from ..models.user import User
from ..schemas.template import TemplateCreate, TemplateUpdate

class TemplateRepository:
    """Repository pattern for template data access."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create(self, user_id: UUID, template_data: TemplateCreate) -> Template:
        """Create a new template."""
        db_template = Template(
            name=template_data.name,
            content=template_data.content,
            description=template_data.description,
            owner_id=user_id,
            team_id=template_data.team_id,
            is_public=template_data.is_public or False,
            tags=template_data.tags or []
        )
        
        self.db.add(db_template)
        await self.db.commit()
        await self.db.refresh(db_template)
        return db_template
    
    async def find_by_id(self, template_id: UUID, user_id: UUID) -> Optional[Template]:
        """Find template by ID with access control."""
        return self.db.query(Template).filter(
            and_(
                Template.id == template_id,
                or_(
                    Template.owner_id == user_id,
                    Template.is_public == True,
                    # TODO: Add team membership check
                )
            )
        ).first()
    
    async def find_user_templates(
        self,
        user_id: UUID,
        team_id: Optional[UUID] = None,
        include_public: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """Find templates for a user with filters."""
        query = self.db.query(Template)
        
        conditions = [Template.owner_id == user_id]
        
        if team_id:
            conditions.append(Template.team_id == team_id)
        
        if include_public:
            conditions.append(Template.is_public == True)
        
        return query.filter(or_(*conditions)).offset(skip).limit(limit).all()
    
    async def update(
        self, 
        template_id: UUID, 
        user_id: UUID, 
        update_data: TemplateUpdate
    ) -> Optional[Template]:
        """Update template with ownership validation."""
        template = self.db.query(Template).filter(
            and_(
                Template.id == template_id,
                Template.owner_id == user_id
            )
        ).first()
        
        if not template:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(template, key, value)
        
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def delete(self, template_id: UUID, user_id: UUID) -> bool:
        """Delete template with ownership validation."""
        result = self.db.query(Template).filter(
            and_(
                Template.id == template_id,
                Template.owner_id == user_id
            )
        ).delete()
        
        await self.db.commit()
        return result > 0
```

## Authentication and Authorization

### Auth Flow
```mermaid
sequenceDiagram
    participant U as User
    participant W as Web App
    participant A as Auth Service
    participant G as GitHub
    participant DB as Database
    participant C as CLI

    Note over U,C: Web Authentication Flow
    
    U->>W: Click "Login with GitHub"
    W->>G: OAuth authorization request
    G-->>U: Authorization page
    U->>G: Approve access
    G->>W: Authorization code
    W->>A: Exchange code for token
    A->>G: Validate token
    G-->>A: User profile data
    A->>DB: Create/update user record
    A-->>W: JWT token + user data
    W->>U: Dashboard (authenticated)

    Note over U,C: CLI Authentication Flow
    
    C->>A: Request CLI auth code
    A-->>C: Display auth URL + code
    U->>W: Enter auth code
    W->>A: Validate auth code
    A->>DB: Generate CLI token
    A-->>C: CLI token
    C->>C: Store token locally
    
    Note over U,C: CLI API Requests
    
    C->>A: API request with CLI token
    A->>A: Validate CLI token
    A->>DB: Execute request
    DB-->>A: Response data
    A-->>C: API response
```

### Middleware/Guards
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import Optional

from ..core.config import settings
from ..core.database import get_db
from ..models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Try JWT token first (web authentication)
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
            
        return user
        
    except JWTError:
        # Try CLI token (CLI authentication)
        user = db.query(User).filter(User.cli_token == credentials.credentials).first()
        if user is None:
            raise credentials_exception
        
        # Update last active timestamp for CLI users
        user.last_active = datetime.utcnow()
        db.commit()
        
        return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active."""
    return current_user

async def require_team_access(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> None:
    """Require user has access to specified team."""
    # Check if user owns the team
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.owner_id == current_user.id)
    ).first()
    
    if team:
        return
    
    # Check if user is a team member
    membership = db.query(TeamMember).filter(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to team"
        )

class RequireRole:
    """Dependency to require specific team role."""
    
    def __init__(self, required_role: str):
        self.required_role = required_role
    
    async def __call__(
        self,
        team_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        membership = db.query(TeamMember).filter(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.user_id == current_user.id
            )
        ).first()
        
        if not membership or membership.role != self.required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {self.required_role}"
            )

# Usage examples
require_admin = RequireRole("admin")
require_editor = RequireRole("editor")
```

# Unified Project Structure

```
promptcraft/
├── .github/                    # CI/CD workflows
│   └── workflows/
│       ├── ci.yaml
│       ├── deploy-web.yaml
│       └── deploy-api.yaml
├── apps/                       # Application packages
│   ├── web/                    # Next.js frontend application
│   │   ├── src/
│   │   │   ├── components/     # UI components
│   │   │   ├── app/            # Next.js app router
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── lib/            # Frontend utilities
│   │   │   ├── stores/         # Zustand state stores
│   │   │   └── styles/         # Global styles and Tailwind
│   │   ├── public/             # Static assets
│   │   ├── tests/              # Frontend tests
│   │   ├── next.config.js
│   │   ├── tailwind.config.js
│   │   └── package.json
│   ├── api/                    # FastAPI backend application
│   │   ├── src/
│   │   │   ├── promptcraft_api/
│   │   │   │   ├── api/        # API endpoints
│   │   │   │   ├── core/       # Core configuration
│   │   │   │   ├── models/     # Database models
│   │   │   │   ├── services/   # Business logic services
│   │   │   │   ├── schemas/    # Pydantic schemas
│   │   │   │   └── utils/      # Backend utilities
│   │   │   └── main.py
│   │   ├── tests/              # Backend tests
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── cli/                    # Enhanced CLI application
│       ├── src/
│       │   └── promptcraft/
│       │       ├── core/       # Core CLI logic
│       │       ├── commands/   # CLI commands
│       │       ├── sync/       # Sync functionality
│       │       └── utils/      # CLI utilities
│       ├── tests/              # CLI tests
│       ├── pyproject.toml
│       └── README.md
├── packages/                   # Shared packages
│   ├── shared/                 # Shared types and utilities
│   │   ├── src/
│   │   │   ├── types/          # TypeScript/Python interfaces
│   │   │   ├── constants/      # Shared constants
│   │   │   └── utils/          # Cross-platform utilities
│   │   ├── package.json
│   │   └── pyproject.toml
│   ├── ui/                     # Shared UI components (Shadcn/ui)
│   │   ├── src/
│   │   │   ├── components/     # Reusable components
│   │   │   └── utils/          # UI utilities
│   │   └── package.json
│   └── config/                 # Shared configuration
│       ├── eslint/
│       │   └── index.js
│       ├── typescript/
│       │   └── tsconfig.json
│       └── jest/
│           └── jest.config.js
├── infrastructure/             # Infrastructure as Code
│   ├── railway/
│   │   └── railway.toml
│   ├── vercel/
│   │   └── vercel.json
│   └── docker-compose.yml      # Local development
├── scripts/                    # Build and deployment scripts
│   ├── build.sh
│   ├── test.sh
│   └── deploy.sh
├── docs/                       # Documentation
│   ├── prd.md
│   ├── front-end-spec.md
│   ├── architecture.md
│   └── api.md
├── .env.example                # Environment template
├── .gitignore
├── package.json                # Root package.json with workspaces
├── turbo.json                  # Turborepo configuration
└── README.md
```

# Development Workflow

## Local Development Setup

### Prerequisites
```bash
# Install Node.js 18+ and Python 3.10+
node --version  # Should be 18.0.0+
python --version  # Should be 3.10+

# Install pnpm for faster package management
npm install -g pnpm

# Install Turborepo for monorepo management
npm install -g turbo

# Install Docker for local services
docker --version
```

### Initial Setup
```bash
# Clone repository
git clone https://github.com/your-org/promptcraft.git
cd promptcraft

# Install all dependencies
pnpm install

# Set up environment files
cp .env.example .env.local
cp apps/api/.env.example apps/api/.env

# Start local database and Redis
docker-compose up -d postgres redis

# Run database migrations
cd apps/api && python -m alembic upgrade head && cd ../..

# Build shared packages
turbo build --filter=@promptcraft/shared
turbo build --filter=@promptcraft/ui
```

### Development Commands
```bash
# Start all services (web, api, cli sync)
turbo dev

# Start frontend only
turbo dev --filter=@promptcraft/web

# Start backend only
turbo dev --filter=@promptcraft/api

# Run tests across all packages
turbo test

# Run specific test suites
turbo test --filter=@promptcraft/web
turbo test --filter=@promptcraft/api
turbo test --filter=@promptcraft/cli

# Build production bundles
turbo build

# Lint and format code
turbo lint
turbo format
```

## Environment Configuration

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

# Deployment Architecture

## Deployment Strategy

**Frontend Deployment:**
- **Platform:** Vercel with Edge Runtime
- **Build Command:** `turbo build --filter=@promptcraft/web`
- **Output Directory:** `apps/web/.next`
- **CDN/Edge:** Global Vercel Edge Network with automatic caching

**Backend Deployment:**
- **Platform:** Railway with PostgreSQL add-on
- **Build Command:** `cd apps/api && pip install -r requirements.txt`
- **Deployment Method:** Docker container with automatic deployments from git

## CI/CD Pipeline

```yaml
name: Deploy PromptCraft

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: promptcraft_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'pnpm'
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          npm install -g pnpm
          pnpm install
          
      - name: Build packages
        run: pnpm turbo build
        
      - name: Run tests
        run: |
          pnpm turbo test
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/promptcraft_test
  
  deploy-web:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          vercel-args: '--prod'
          working-directory: ./apps/web

  deploy-api:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      - uses: bltavares/actions-railway@v0.3.0
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
          service: 'promptcraft-api'
          detach: true
```

## Environments

| Environment | Frontend URL | Backend URL | Purpose |
|-------------|--------------|-------------|---------|
| Development | http://localhost:3000 | http://localhost:8000 | Local development |
| Staging | https://staging.promptcraft.dev | https://api-staging.promptcraft.dev | Pre-production testing |
| Production | https://promptcraft.dev | https://api.promptcraft.dev | Live environment |

# Security and Performance

## Security Requirements

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

## Performance Optimization

**Frontend Performance:**
- Bundle Size Target: <500KB initial bundle, <50KB route chunks
- Loading Strategy: Lazy loading for routes, component-level code splitting
- Caching Strategy: SWR for API data, Service Worker for static assets

**Backend Performance:**
- Response Time Target: <100ms for template operations, <50ms for auth
- Database Optimization: Connection pooling, query optimization, proper indexing
- Caching Strategy: Redis for session data, API response caching with 5-minute TTL

# Testing Strategy

## Testing Pyramid
```
           E2E Tests (Playwright)
          /                    \
    Integration Tests (API/DB)
   /                            \
Frontend Unit (Vitest)    Backend Unit (Pytest)
```

## Test Organization

### Frontend Tests
```
apps/web/tests/
├── __mocks__/              # Mock implementations
├── components/             # Component unit tests
│   ├── TemplateCard.test.tsx
│   └── Dashboard.test.tsx
├── hooks/                  # Custom hook tests
│   └── useTemplates.test.ts
├── pages/                  # Page integration tests
│   └── dashboard.test.tsx
├── utils/                  # Utility function tests
│   └── api-client.test.ts
└── setup.ts                # Test setup configuration
```

### Backend Tests
```
apps/api/tests/
├── conftest.py             # Pytest configuration
├── unit/                   # Unit tests
│   ├── services/
│   │   └── test_template_service.py
│   └── utils/
│       └── test_helpers.py
├── integration/            # Integration tests
│   ├── test_auth_endpoints.py
│   ├── test_template_endpoints.py
│   └── test_sync_endpoints.py
└── fixtures/               # Test data fixtures
    └── templates.py
```

### E2E Tests
```
tests/e2e/
├── specs/
│   ├── template-creation.spec.ts
│   ├── team-collaboration.spec.ts
│   └── cli-sync.spec.ts
├── fixtures/
│   └── test-data.ts
├── pages/                  # Page object models
│   ├── dashboard.page.ts
│   └── editor.page.ts
└── playwright.config.ts
```

## Test Examples

### Frontend Component Test
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'
import { TemplateCard } from '@/components/templates/TemplateCard'
import { Template } from '@/types/template'

const mockTemplate: Template = {
  id: '1',
  name: 'test-template',
  content: 'Hello $ARGUMENTS',
  description: 'Test template',
  owner_id: 'user1',
  team_id: null,
  is_public: false,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z',
  usage_count: 5,
  tags: ['test']
}

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('TemplateCard', () => {
  it('renders template information correctly', () => {
    renderWithProviders(<TemplateCard template={mockTemplate} />)
    
    expect(screen.getByText('test-template')).toBeInTheDocument()
    expect(screen.getByText('Test template')).toBeInTheDocument()
    expect(screen.getByText('5 uses')).toBeInTheDocument()
  })
  
  it('calls onEdit when edit button is clicked', async () => {
    const onEdit = vi.fn()
    
    renderWithProviders(
      <TemplateCard template={mockTemplate} onEdit={onEdit} />
    )
    
    const editButton = screen.getByRole('button', { name: /edit/i })
    fireEvent.click(editButton)
    
    await waitFor(() => {
      expect(onEdit).toHaveBeenCalledTimes(1)
    })
  })
  
  it('shows team badge for team templates', () => {
    const teamTemplate = { ...mockTemplate, team_id: 'team1' }
    
    renderWithProviders(<TemplateCard template={teamTemplate} />)
    
    expect(screen.getByText('Team')).toBeInTheDocument()
  })
})
```

### Backend API Test
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from src.promptcraft_api.models.template import Template
from src.promptcraft_api.models.user import User

@pytest.mark.asyncio
async def test_create_template_success(
    client: AsyncClient,
    db: Session,
    auth_headers: dict,
    test_user: User
):
    """Test successful template creation."""
    template_data = {
        "name": "test-template",
        "content": "Hello $ARGUMENTS",
        "description": "Test template",
        "is_public": False,
        "tags": ["test"]
    }
    
    response = await client.post(
        "/templates",
        json=template_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "test-template"
    assert data["content"] == "Hello $ARGUMENTS"
    assert data["owner_id"] == str(test_user.id)
    
    # Verify template was created in database
    template = db.query(Template).filter(Template.name == "test-template").first()
    assert template is not None
    assert template.owner_id == test_user.id

@pytest.mark.asyncio
async def test_create_template_duplicate_name(
    client: AsyncClient,
    db: Session,
    auth_headers: dict,
    test_user: User
):
    """Test creating template with duplicate name fails."""
    # Create first template
    template1 = Template(
        name="duplicate-name",
        content="First template",
        owner_id=test_user.id
    )
    db.add(template1)
    db.commit()
    
    # Try to create second template with same name
    template_data = {
        "name": "duplicate-name",
        "content": "Second template"
    }
    
    response = await client.post(
        "/templates",
        json=template_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_templates_filters(
    client: AsyncClient,
    auth_headers: dict,
    sample_templates: list[Template]
):
    """Test template listing with filters."""
    # Test public filter
    response = await client.get(
        "/templates?public=true",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    public_templates = [t for t in data["templates"] if t["is_public"]]
    assert len(public_templates) == len([t for t in sample_templates if t.is_public])
```

### E2E Test
```typescript
import { test, expect } from '@playwright/test'

test.describe('Template Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.click('text=Login with GitHub')
    // Mock OAuth flow or use test user
    await page.waitForURL('/dashboard')
  })

  test('should create a new template', async ({ page }) => {
    // Navigate to template creation
    await page.click('text=New Template')
    await expect(page).toHaveURL('/dashboard/templates/new')
    
    // Fill template form
    await page.fill('[data-testid="template-name"]', 'e2e-test-template')
    await page.fill('[data-testid="template-description"]', 'E2E test template')
    
    // Fill template content
    const editor = page.locator('[data-testid="template-editor"]')
    await editor.fill('# Hello $ARGUMENTS\n\nThis is a test template.')
    
    // Test template with arguments
    await page.fill('[data-testid="test-arguments"]', 'World')
    await page.click('[data-testid="preview-button"]')
    
    // Verify preview
    await expect(page.locator('[data-testid="preview-content"]'))
      .toContainText('Hello World')
    
    // Save template
    await page.click('[data-testid="save-template"]')
    
    // Verify success message
    await expect(page.locator('[data-testid="success-message"]'))
      .toContainText('Template created successfully')
    
    // Verify redirect to dashboard
    await expect(page).toHaveURL('/dashboard')
    
    // Verify template appears in list
    await expect(page.locator('[data-testid="template-list"]'))
      .toContainText('e2e-test-template')
  })

  test('should sync template with CLI', async ({ page, request }) => {
    // Create template via web interface
    await page.click('text=New Template')
    await page.fill('[data-testid="template-name"]', 'cli-sync-test')
    await page.fill('[data-testid="template-content"]', 'CLI sync: $ARGUMENTS')
    await page.click('[data-testid="save-template"]')
    
    // Simulate CLI sync request
    const syncResponse = await request.post('/api/sync/cli', {
      data: {
        local_templates: []
      },
      headers: {
        'Authorization': 'Bearer test-cli-token'
      }
    })
    
    expect(syncResponse.status()).toBe(200)
    
    const syncData = await syncResponse.json()
    expect(syncData.updates).toContainEqual(
      expect.objectContaining({
        name: 'cli-sync-test',
        content: 'CLI sync: $ARGUMENTS'
      })
    )
  })
})
```

# Coding Standards

## Critical Fullstack Rules

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

## Naming Conventions

| Element | Frontend | Backend | Example |
|---------|----------|---------|---------|
| Components | PascalCase | - | `TemplateCard.tsx` |
| Hooks | camelCase with 'use' | - | `useTemplates.ts` |
| API Routes | - | kebab-case | `/api/user-templates` |
| Database Tables | - | snake_case | `user_templates` |
| Python Functions | - | snake_case | `create_template` |
| TypeScript Functions | camelCase | - | `createTemplate` |
| Environment Variables | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE | `DATABASE_URL` |
| CSS Classes | kebab-case | - | `template-card` |

# Error Handling Strategy

## Error Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant DB as Database
    participant Log as Logger

    C->>API: Request with invalid data
    API->>API: Validate request
    API->>Log: Log validation error
    API-->>C: 400 Bad Request

    C->>API: Valid request
    API->>DB: Database operation
    DB-->>API: Database error
    API->>Log: Log database error
    API-->>C: 500 Internal Server Error

    C->>API: Unauthorized request
    API->>API: Check authentication
    API->>Log: Log auth failure
    API-->>C: 401 Unauthorized
```

## Error Response Format

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

## Frontend Error Handling

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

## Backend Error Handling

```python
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from typing import Any, Dict
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptCraftError(Exception):
    """Base exception for PromptCraft application errors."""
    
    def __init__(self, code: str, message: str, details: Dict[str, Any] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(PromptCraftError):
    """Validation error exception."""
    pass

class AuthenticationError(PromptCraftError):
    """Authentication error exception."""
    pass

class AuthorizationError(PromptCraftError):
    """Authorization error exception."""
    pass

class NotFoundError(PromptCraftError):
    """Resource not found exception."""
    pass

class ConflictError(PromptCraftError):
    """Resource conflict exception."""
    pass

def create_error_response(
    code: str,
    message: str,
    status_code: int = 500,
    details: Dict[str, Any] = None,
    request_id: str = None
) -> JSONResponse:
    """Create standardized error response."""
    
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex[:8]}"
    
    error_data = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "requestId": request_id
        }
    }
    
    return JSONResponse(
        status_code=status_code,
        content=error_data
    )

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all unhandled exceptions."""
    
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    
    logger.error(
        f"Unhandled exception for request {request_id}: {exc}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "url": str(request.url),
            "method": request.method,
        }
    )
    
    # Handle PromptCraft custom exceptions
    if isinstance(exc, ValidationError):
        return create_error_response(
            code=exc.code,
            message=exc.message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=exc.details,
            request_id=request_id
        )
    elif isinstance(exc, AuthenticationError):
        return create_error_response(
            code=exc.code,
            message=exc.message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            request_id=request_id
        )
    elif isinstance(exc, AuthorizationError):
        return create_error_response(
            code=exc.code,
            message=exc.message,
            status_code=status.HTTP_403_FORBIDDEN,
            request_id=request_id
        )
    elif isinstance(exc, NotFoundError):
        return create_error_response(
            code=exc.code,
            message=exc.message,
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id
        )
    elif isinstance(exc, ConflictError):
        return create_error_response(
            code=exc.code,
            message=exc.message,
            status_code=status.HTTP_409_CONFLICT,
            details=exc.details,
            request_id=request_id
        )
    
    # Handle FastAPI validation errors
    elif isinstance(exc, RequestValidationError):
        return create_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": exc.errors()},
            request_id=request_id
        )
    
    # Handle database integrity errors
    elif isinstance(exc, IntegrityError):
        return create_error_response(
            code="CONSTRAINT_VIOLATION",
            message="Database constraint violation",
            status_code=status.HTTP_409_CONFLICT,
            request_id=request_id
        )
    
    # Handle all other exceptions
    else:
        return create_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An internal server error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id
        )

# Usage in services
class TemplateService:
    async def create_template(self, user_id: str, template_data: TemplateCreate) -> Template:
        try:
            # Validate template name uniqueness
            existing = await self.repository.find_by_name(
                name=template_data.name,
                user_id=user_id,
                team_id=template_data.team_id
            )
            
            if existing:
                raise ConflictError(
                    code="TEMPLATE_NAME_EXISTS",
                    message=f"Template '{template_data.name}' already exists",
                    details={
                        "name": template_data.name,
                        "existing_id": str(existing.id)
                    }
                )
            
            # Create template
            template = await self.repository.create(user_id, template_data)
            return template
            
        except IntegrityError as e:
            logger.error(f"Database integrity error creating template: {e}")
            raise ConflictError(
                code="TEMPLATE_CONSTRAINT_VIOLATION",
                message="Template creation failed due to constraint violation"
            )
        except Exception as e:
            logger.error(f"Unexpected error creating template: {e}")
            raise PromptCraftError(
                code="TEMPLATE_CREATION_FAILED",
                message="Failed to create template"
            )
```

# Monitoring and Observability

## Monitoring Stack

- **Frontend Monitoring:** Vercel Analytics + Sentry for error tracking and performance monitoring
- **Backend Monitoring:** Railway metrics + Sentry for API error tracking and performance
- **Error Tracking:** Sentry integrated across frontend, backend, and CLI for unified error reporting
- **Performance Monitoring:** Web Vitals tracking, API response time monitoring, CLI execution time tracking

## Key Metrics

**Frontend Metrics:**
- Core Web Vitals (LCP, FID, CLS)
- JavaScript errors and error boundaries
- API response times from client perspective
- User interactions and feature usage

**Backend Metrics:**
- Request rate (requests per minute)
- Error rate (4xx/5xx responses)
- Response time (p50, p95, p99 percentiles)
- Database query performance and connection pool metrics

**CLI Metrics:**
- Command execution time (<150ms requirement)
- Sync operation success/failure rates
- Template processing performance
- Cross-platform compatibility issues

**Business Metrics:**
- Template creation and usage rates
- Team collaboration activity
- User retention and engagement
- Feature adoption rates

# Checklist Results Report

## Full-Stack Architecture Completion Summary

✅ **Architecture Design Complete**: Comprehensive full-stack architecture designed for PromptCraft evolution from CLI tool to collaborative platform

✅ **Technology Stack Finalized**: Modern tech stack selected with Python/FastAPI backend, Next.js frontend, and PostgreSQL database

✅ **Integration Strategy Defined**: Hybrid approach maintaining CLI performance while adding web collaboration capabilities

✅ **Performance Requirements Addressed**: Sub-150ms CLI performance maintained through optimized sync mechanisms and caching strategies

✅ **Security Framework Established**: JWT authentication, OAuth integration, and comprehensive security measures across all layers

✅ **Development Workflow Defined**: Monorepo structure with Turborepo, comprehensive testing strategy, and CI/CD pipeline

✅ **Deployment Architecture Planned**: Vercel + Railway deployment strategy with global CDN and auto-scaling capabilities

✅ **Monitoring Strategy Implemented**: Comprehensive observability with Sentry, performance tracking, and business metrics

**Key Architectural Decisions Made:**
- Hybrid CLI + Web architecture preserving existing performance
- Monorepo with shared TypeScript interfaces for type safety
- Real-time synchronization via WebSocket + API polling fallback  
- File-system + database dual storage for optimal performance
- Modern developer-focused tech stack with excellent TypeScript support

**Next Implementation Priority:**
1. Set up monorepo structure and shared packages
2. Implement core API endpoints for template management
3. Build CLI synchronization functionality
4. Develop web interface for team collaboration
5. Deploy and test cross-platform compatibility

The architecture successfully balances the need to maintain CLI tool performance while enabling rich team collaboration features through a modern, scalable web platform.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create comprehensive full-stack architecture for PromptCraft", "status": "completed", "activeForm": "Creating comprehensive full-stack architecture for PromptCraft"}, {"content": "Generate complete architecture document", "status": "completed", "activeForm": "Generating complete architecture document"}, {"content": "Review and validate architecture decisions", "status": "completed", "activeForm": "Reviewing and validating architecture decisions"}]