# EDITH OS Engineering Rules

**Status:** Active architecture policy  
**Applies from:** Sprint 11.2 onward  
**Purpose:** Keep EDITH modular, lightweight, observable, and extensible as it grows from a local assistant into an operating system layer.

## 1. Subsystem ownership

Every capability belongs to exactly one owner subsystem. A feature may collaborate with other subsystems through contracts, but it must not have ambiguous ownership.

| Subsystem | Owns |
| --- | --- |
| Brain | Intent understanding, planning, decision-making, orchestration, and response composition. |
| Memory | Session state, durable facts, preferences, retrieval, retention, and deletion. |
| Skills | Bounded actions against the operating system and external capabilities. |
| Context | Active application, window, file, selection, task, and environment state. |
| Perception | Voice input, screen capture, OCR, camera, vision, and signal normalization. |
| Security | Identity, permissions, consent, secrets, auditing, and policy decisions. |
| Interface | CLI, desktop, mobile, accessibility, streaming output, and visible status. |

Do not add miscellaneous top-level capability modules. Place it in one of these domains or create an architecture decision record before introducing a new domain.

## 2. Mandatory feature design record

Before implementation, every feature must answer the following five questions in its issue, sprint note, or architecture decision record:

1. **Who plans it?** Which Brain component creates or approves the task?
2. **Who executes it?** Which Skill or subsystem performs the actual work?
3. **Which subsystem owns it?** Identify one owner from the table above.
4. **How is state updated?** State the source of truth, events emitted, and any memory/context update.
5. **What `ActionResult` is returned?** Define success data, user-safe message, failure modes, and side effects.

### Required feature record template

```md
## Feature: <name>

- Planner: <component or rule>
- Executor: <skill/subsystem>
- Owner subsystem: <Brain | Memory | Skills | Context | Perception | Security | Interface>
- State updates: <events, store, retention, cleanup>
- ActionResult: <success payload, failure codes, side effects>
```

## 3. Layering and execution flow

The normal control flow is:

```text
Interface
  -> Brain
  -> Memory
  -> Skills
  -> Operating System
```

The current `Planner -> TaskQueue -> Executor -> ToolManager -> Skill` path is the Skills-layer execution contract. A user interface must not call a Skill directly. A Skill must not call the user interface, planner, or memory store directly. Cross-subsystem collaboration happens through explicit application contracts and events.

`TaskQueue` owns task lifecycle state and FIFO order. The executor consumes only queued work and stops after a failed task by default, preserving later tasks for inspection, cancellation, or manual retry.

## 4. Lazy loading and event-driven work

- Load a module only when an active request or registered event requires it.
- Release hardware handles, watchers, model sessions, and provider clients when the owning request ends unless a documented shared lifecycle exists.
- Prefer operating-system notifications, file-system events, accessibility events, webhooks, and callbacks over polling.
- Do not introduce a long-running thread merely to wait for work. Use a queue, callback, or event subscription.
- Any exception to these rules must document why polling or residency is required, its interval, and its performance impact.

## 5. Skill contract

Every new skill must expose metadata that permits discovery without executing the skill.

```python
class ExampleSkill(BaseTool):
    NAME = "example"
    DESCRIPTION = "One sentence describing the capability."
    RESOURCE_PROFILE = "on_demand"  # e.g. on_demand, file_system, browser, device
    SUPPORTED_ACTIONS = {"action_name"}

    def execute(self, task: Task) -> ActionResult:
        ...
```

Rules:

- `NAME` is stable and unique; `Task.tool` resolves to it.
- `SUPPORTED_ACTIONS` is the authoritative action list used by the planner and decision engine.
- `ToolManager.get_capabilities()` is the discovery surface for installed skill metadata. It does not execute skills or create background work.
- `execute(task)` receives structured data only: `task.action`, `task.target`, and `task.parameters`.
- Skills do not parse natural language, print output, plan follow-up work, or reach into another skill.
- State-changing operating-system skills must require an explicit confirmation before their first execution.
- `ToolManager.process()` remains a temporary compatibility adapter for legacy text callers. It may parse text only at that boundary and must convert it to a `Task` before skill execution.

## 6. ActionResult contract

Every new skill returns an `ActionResult`; raw strings are not a new public execution contract.

```python
@dataclass
class ActionResult:
    success: bool
    message: str                 # Safe for the user interface
    data: object | None = None
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict = field(default_factory=dict)
```

The Interface owns rendering `ActionResult.message`. Skills never print directly. The executor may use `success` to decide whether a multi-step workflow should stop, retry, or report partial completion.

## 7. Performance budget

EDITH must remain lightweight on its local host.

| Metric | Target |
| --- | --- |
| Idle CPU | Less than 1% |
| Idle RAM | Less than 300 MB |
| Cold start | Less than 2 seconds |
| Non-LLM command latency | Less than 300 ms |

Every new background service, model, watcher, cache, or dependency must state how it fits inside this budget. Measure non-LLM command latency at the executor boundary, excluding user confirmation time.

## 8. Extension policy

- Extend contracts and add adapters; do not rewrite working architecture without a documented reason.
- Maintain backward compatibility at public boundaries during migrations.
- Deprecate old paths explicitly and remove them only in a planned sprint with tests.
- Do not bypass `Planner -> Executor -> ToolManager -> Skill` for actions created by EDITH.

## 9. Sprint completion checklist

Before marking a sprint complete, verify:

- [ ] One owning subsystem is named.
- [ ] The five mandatory design questions are answered.
- [ ] New skills declare all metadata.
- [ ] New skill execution returns `ActionResult` and does not print.
- [ ] Lazy-loading and event-driven behavior were considered.
- [ ] Performance impact was measured or bounded.
- [ ] Layering was preserved.
- [ ] Compatibility behavior and tests are documented.
- [ ] Duplicate parsing, duplicated state, and duplicated capability logic were removed or justified.

## 10. Migration boundary

Sprint 11.1 established structured `Task` dispatch. Sprint 11.2 introduced `ActionResult` and migrated all active skills while preserving `ToolManager.process()` as the legacy text-input boundary.

From this point onward, all new or materially changed skills must return `ActionResult` immediately. Any remaining legacy return path must be migrated additively, with compatibility tests at its public boundary.
