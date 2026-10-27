# Sprint 15.1: Clipboard & Selection Awareness

## Architecture Checklist
1. **Who plans it?** `Planner`, by detecting the exact string `clipboard` inside user input.
2. **Who executes it?** `ContextManager` acts as the data provider via `pbpaste`.
3. **Which subsystem owns it?** Context.
4. **How is state updated?** Executes `subprocess.run(["pbpaste"])` to fetch clipboard data.
5. **What ActionResult is returned?** An `ActionResult` containing the `clipboard` string under `data`.

## Summary
The Context subsystem was extended to natively read the macOS clipboard contents using the `pbpaste` command. The Planner now resolves the token `clipboard` similarly to `this`, dynamically substituting clipboard text into commands like `remember data is clipboard` prior to task generation.
