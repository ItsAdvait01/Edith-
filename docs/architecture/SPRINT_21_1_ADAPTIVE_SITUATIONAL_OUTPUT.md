# Sprint 21.1 — Adaptive & Situational Output Architecture

- **Planner / CLI Intercept:** Direct CLI matching in `app.py` for `/mode`, `/mode driving`, `/mode desk`, `/mode meeting`, `/mode default`, as well as natural phrases (`"i am driving"`, `"driving mode"`, `"switch to meeting"`).
- **Executor / Renderer:** `OutputRouter.render_for_mode(mode, action_result, response_text)` dispatches tailored visual and auditory outputs based on situational context.
- **Owner Subsystems:** Voice & Context Subsystems (`src/voice/output_router.py`, `src/context/situation_detector.py`).
- **State Updates:** In-memory `SituationDetector` tracks active situational profile. Zero disk I/O, zero background services.
- **ActionResult / RenderOutput:** Returns typed `RenderOutput` with `.screen` (visual text/card), `.voice` (spoken sentence), `.follow_up` (interactive spoken prompt), and `.mode`.

## Situational Profiles

1. **🚗 Driving Mode (`driving`)**
   - **Visual:** Suppressed (`screen=None` displays minimal `✅` indicator to keep driver eyes on the road).
   - **Voice:** Crisp spoken summary of top 2–3 items or core status fields.
   - **Interaction:** Follow-up hands-free prompt randomly chosen from tactical cues (*e.g., "Want me to navigate to the first one?"*, *"Should I pull up directions in Maps?"*).

2. **🖥 Desk Mode (`desk`)**
   - **Visual:** Full Unicode terminal card with key-value data, borders, and action hints (`↳ Ask a follow-up anytime`).
   - **Voice:** Executive thesis / spoken card summary.

3. **🤫 Meeting Mode (`meeting`)**
   - **Visual:** Single compact line notification (`📌 🔋 Battery Status: 74% · Discharging`).
   - **Voice:** Completely muted (`voice=None`).

4. **⚡ Default Mode (`default`)**
   - **Visual:** Adaptive formatting (Unicode card for structured tools; plain text for conversational chats).
   - **Voice:** Natural sentence framing or executive notice.

## Resource Profile
- Zero external libraries or terminal dependencies. Pure Python box-drawing unicode characters (`╭`, `─`, `╮`, `│`, `├`, `┬`, `┴`, `╰`).
- 0% idle CPU overhead.
