# User

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
