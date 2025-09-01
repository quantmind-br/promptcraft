# Backend Error Handling

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
