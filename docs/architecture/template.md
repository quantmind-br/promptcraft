# Template

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
