# Component Architecture

### Component Organization
```
src/
├── components/
│   ├── ui/                 # Shadcn/ui base components
│   ├── templates/         # Template-specific components
│   ├── teams/             # Team management components
│   ├── layout/            # Layout components
│   └── common/            # Shared components
├── pages/                 # Next.js pages
├── hooks/                 # Custom React hooks
├── lib/                   # Utility functions
├── stores/                # Zustand state stores
└── types/                 # TypeScript type definitions
```

### Component Template
```typescript
import { cn } from '@/lib/utils'
import { forwardRef } from 'react'

interface TemplateCardProps extends React.HTMLAttributes<HTMLDivElement> {
  template: Template
  onEdit?: () => void
  onDelete?: () => void
  variant?: 'default' | 'compact'
}

const TemplateCard = forwardRef<HTMLDivElement, TemplateCardProps>(
  ({ template, onEdit, onDelete, variant = 'default', className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border bg-card text-card-foreground shadow-sm',
          variant === 'compact' && 'p-3',
          variant === 'default' && 'p-6',
          className
        )}
        {...props}
      >
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="font-semibold leading-none">{template.name}</h3>
            {template.description && (
              <p className="text-sm text-muted-foreground">
                {template.description}
              </p>
            )}
          </div>
          <TemplateCardActions 
            onEdit={onEdit} 
            onDelete={onDelete}
          />
        </div>
        <TemplateCardFooter template={template} />
      </div>
    )
  }
)

TemplateCard.displayName = 'TemplateCard'

export { TemplateCard, type TemplateCardProps }
```
