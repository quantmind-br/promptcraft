# Database Architecture

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
