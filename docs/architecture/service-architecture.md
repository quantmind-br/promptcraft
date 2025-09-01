# Service Architecture

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
