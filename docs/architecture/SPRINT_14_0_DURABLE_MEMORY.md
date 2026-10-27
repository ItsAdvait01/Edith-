# Sprint 14.0 - Durable Memory Design

- **Planner:** Planner maps natural language inputs (`remember <key> is <value>`, `recall <key>`, `forget <key>`) to memory tasks (implemented in Sprint 13.2).
- **Executor:** No change.
- **Owner subsystem:** Memory.
- **State updates:** Facts are loaded from and saved to a local JSON file (`~/.edith_memory.json`) in the user's home directory.
- **ActionResult:** `MemoryTool` returns success/failure with the retrieved fact or confirmation of storage.

## Features
- The `MemoryStore` is no longer fully ephemeral. It saves and loads facts from a local JSON file.
- Preserves the local-first philosophy by keeping data on disk without relying on external databases or cloud services.
- The `MemoryTool` remains structurally identical, delegating the persistence transparently to `MemoryStore`.
