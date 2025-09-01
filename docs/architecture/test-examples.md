# Test Examples

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
