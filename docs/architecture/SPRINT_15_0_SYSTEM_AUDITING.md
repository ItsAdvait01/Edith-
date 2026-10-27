# Sprint 15.0: System Auditing

## Architecture Checklist
1. **Who plans it?** N/A (Security audit runs transparently across all tools).
2. **Who executes it?** `AuditLogger` instantiated inside `Executor`.
3. **Which subsystem owns it?** Security.
4. **How is state updated?** Appends JSON representation of task and execution outcome to `~/.edith_audit.log`.
5. **What ActionResult is returned?** Unchanged; runs as a side-effect after task execution.

## Summary
To ensure traceability and safe historical visibility, we introduced an `AuditLogger` inside the Security subsystem. Every task processed by the `Executor` is now recorded to an append-only JSONL log `~/.edith_audit.log`.
