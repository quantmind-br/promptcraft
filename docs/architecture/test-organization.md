# Test Organization

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
