# Architectural Patterns

- **Hybrid Architecture:** CLI-first with web collaboration layer - _Rationale:_ Preserves CLI performance while enabling team features
- **API-First Design:** RESTful APIs with WebSocket real-time sync - _Rationale:_ Ensures consistency between CLI and web interfaces
- **Component-Based UI:** React with TypeScript and Tailwind CSS - _Rationale:_ Developer-familiar stack with excellent TypeScript support
- **Repository Pattern:** Abstract data access for both file system and database - _Rationale:_ Enables flexible storage backends and testing
- **Event-Driven Sync:** WebSocket events for real-time template updates - _Rationale:_ Immediate synchronization between CLI and web users
- **Monorepo Pattern:** Shared types and utilities across CLI, API, and web - _Rationale:_ Ensures type safety and code reuse across the entire stack
