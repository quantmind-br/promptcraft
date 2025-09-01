# State Management Architecture

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
