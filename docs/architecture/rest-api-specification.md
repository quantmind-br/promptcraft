# REST API Specification

```yaml
openapi: 3.0.0
info:
  title: PromptCraft API
  version: 1.0.0
  description: REST API for PromptCraft template management and synchronization
servers:
  - url: https://api.promptcraft.dev
    description: Production API server

paths:
  /auth/login:
    post:
      summary: Authenticate user with GitHub OAuth
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                code:
                  type: string
                  description: GitHub OAuth authorization code
      responses:
        '200':
          description: Authentication successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  user:
                    $ref: '#/components/schemas/User'
  
  /templates:
    get:
      summary: List user templates
      parameters:
        - name: team_id
          in: query
          schema:
            type: string
        - name: public
          in: query
          schema:
            type: boolean
      responses:
        '200':
          description: List of templates
          content:
            application/json:
              schema:
                type: object
                properties:
                  templates:
                    type: array
                    items:
                      $ref: '#/components/schemas/Template'
    post:
      summary: Create new template
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TemplateCreate'
      responses:
        '201':
          description: Template created successfully
  
  /templates/{id}:
    get:
      summary: Get template by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Template details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Template'
    put:
      summary: Update template
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TemplateUpdate'
      responses:
        '200':
          description: Template updated successfully
    delete:
      summary: Delete template
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '204':
          description: Template deleted successfully

  /sync/cli:
    post:
      summary: Sync CLI templates with server
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                local_templates:
                  type: array
                  items:
                    $ref: '#/components/schemas/LocalTemplate'
      responses:
        '200':
          description: Sync result
          content:
            application/json:
              schema:
                type: object
                properties:
                  conflicts:
                    type: array
                    items:
                      $ref: '#/components/schemas/SyncConflict'
                  updates:
                    type: array
                    items:
                      $ref: '#/components/schemas/Template'

components:
  schemas:
    Template:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        content:
          type: string
        description:
          type: string
        owner_id:
          type: string
        team_id:
          type: string
        is_public:
          type: boolean
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        usage_count:
          type: integer
        tags:
          type: array
          items:
            type: string
    
    User:
      type: object
      properties:
        id:
          type: string
        email:
          type: string
        name:
          type: string
        github_id:
          type: string
        preferences:
          type: object
        created_at:
          type: string
          format: date-time
        last_active:
          type: string
          format: date-time

    TemplateCreate:
      type: object
      required:
        - name
        - content
      properties:
        name:
          type: string
        content:
          type: string
        description:
          type: string
        team_id:
          type: string
        is_public:
          type: boolean
        tags:
          type: array
          items:
            type: string

    TemplateUpdate:
      type: object
      properties:
        name:
          type: string
        content:
          type: string
        description:
          type: string
        is_public:
          type: boolean
        tags:
          type: array
          items:
            type: string

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []
```
