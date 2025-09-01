# CLI Agent

**Responsibility:** Maintains existing CLI functionality while adding synchronization capabilities

**Key Interfaces:**
- Local file system operations
- Template discovery and processing
- API synchronization endpoints
- Clipboard integration

**Dependencies:** FastAPI backend for sync, local file system for templates

**Technology Stack:** Python 3.10+, click, pyperclip, httpx for API calls, asyncio for background sync
