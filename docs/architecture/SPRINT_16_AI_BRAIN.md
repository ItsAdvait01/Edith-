# Sprint 16.0–16.2: AI-Powered Brain

## Architecture Checklist
1. **Who plans it?** `AIPlanner` — new LLM-driven Brain component using gemma3:4b via Ollama.
2. **Who executes it?** Unchanged — `Executor` → `ToolManager` → `Skill`.
3. **Which subsystem owns it?** Brain.
4. **How is state updated?** AIPlanner generates validated `Task` objects into `TaskQueue`, same as the rule-based planner.
5. **What ActionResult is returned?** Unchanged — skills return the same `ActionResult`.

## Summary
The Brain subsystem was upgraded with a layered planning architecture:

1. **Rule-based planner** runs first (instant, handles known patterns like `open chrome`).
2. **AI planner** runs only when the rule-based planner has no match — sends the request to gemma3:4b via Ollama with a structured system prompt.
3. **Chat fallback** runs if neither planner produces tasks.

The AI planner validates every LLM-generated task against registered capabilities, rejecting hallucinated tools and invalid actions. It handles Ollama failures, malformed JSON, and markdown code fences gracefully.

## Key Design Decisions
- Non-streaming Ollama call (need complete JSON, not tokens)
- No retries on malformed JSON (avoid loops and latency)
- 10-second timeout (fail fast if Ollama is down)
- Rule-based planner preserved as fast path (no LLM call for known patterns)
