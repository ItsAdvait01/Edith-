# Sprint 13.0 - Browser Skill Foundation Design

- **Planner:** Recognizes `open <url>` mapping to `browser:open_url`, and `search <query>` mapping to `browser:search`.
- **Executor:** No change.
- **Owner subsystem:** Skills owns the `BrowserTool`.
- **State updates:** No new state.
- **ActionResult:** Returns success/failure with the URL opened in data payload.

## Features
- `BrowserTool` uses macOS `open` to open URLs in the default browser.
- URL validation (requires http/https scheme) for `open_url` action.
- URL encoding for search queries.
- Plugs into existing structured task execution pipeline.
