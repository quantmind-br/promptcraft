# Team

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
