# Deployment Strategy

**Frontend Deployment:**
- **Platform:** Vercel with Edge Runtime
- **Build Command:** `turbo build --filter=@promptcraft/web`
- **Output Directory:** `apps/web/.next`
- **CDN/Edge:** Global Vercel Edge Network with automatic caching

**Backend Deployment:**
- **Platform:** Railway with PostgreSQL add-on
- **Build Command:** `cd apps/api && pip install -r requirements.txt`
- **Deployment Method:** Docker container with automatic deployments from git
