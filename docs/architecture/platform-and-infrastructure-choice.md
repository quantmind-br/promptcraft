# Platform and Infrastructure Choice

**Platform:** Vercel + Railway
**Key Services:** Vercel Edge Functions, Railway PostgreSQL, Redis for caching, GitHub for authentication
**Deployment Host and Regions:** Global edge deployment via Vercel CDN, Railway US-West for API

**Rationale:** This combination provides optimal developer experience with zero-config deployments, automatic scaling, and excellent performance for both CLI sync operations and web interface. Railway offers superior database performance compared to serverless alternatives while maintaining cost efficiency.
