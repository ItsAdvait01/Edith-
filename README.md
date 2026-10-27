# EDITH OS ⚡

> **A Lightweight, Local-First Personal AI Assistant & OS Layer for Apple Silicon**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 117 Passing](https://img.shields.io/badge/Tests-117%20Passed-brightgreen.svg)]()
[![Platform: macOS Apple Silicon](https://img.shields.io/badge/Platform-macOS%20(M1%2FM2%2FM3)-blue.svg)]()
[![Dependencies: 0 Idle Overhead](https://img.shields.io/badge/Idle%20CPU-0%25-green.svg)]()

EDITH is a modular, event-driven personal AI operating system layer built from the ground up to run on single-user Apple Silicon MacBooks (optimized for fanless MacBook Air M1). It bridges high-level natural language intent directly to native macOS system controls, files, browsers, and terminal execution with strict safety policies and proactive power awareness.

---

## 🌟 Key Highlights

- **🧠 Layered Cognitive Architecture:** 
  Deterministic rule-based fast path ($\approx 0\text{ms}$) $\to$ Local LLM AI planner (via Ollama) $\to$ Conversational chat fallback.
- **🔋 Battery-Aware Intelligence (`PowerManager`):** 
  Queries real-time macOS power telemetry (`pmset`) and throttles redundant speculative inference passes on battery to protect fanless M1 MacBooks from thermal throttling and battery drain.
- **🎙 F.R.I.D.A.Y. Tactical Persona & Dual-Channel Audio:** 
  Native macOS TTS (`say`) integration with dynamic tone shifting. Displays detailed code/tables visually on-screen while speaking a synthesized executive summary aloud.
- **🚗 Situational Awareness Modes:** 
  Dynamically adapts output format across four real-world contexts:
  - **Driving:** Voice-only concise summaries with hands-free follow-up queries.
  - **Desk:** Full Unicode terminal cards with action suggestions.
  - **Meeting:** Silent, single-line glanceable notifications.
  - **Default:** Adaptive smart selection.
- **👁 Multimodal Vision Understanding:** 
  Zero-clutter screen understanding (`analyze screen`). Captures a temporary, transient snapshot to cache, invokes vision models (`llava` or cloud multimodal APIs), and auto-cleans temp assets.
- **🛡 4-Tier Command Policy & Safety Staging:** 
  Stateless risk classification (`none`, `low`, `high`, `destructive`). Read-only terminal operations execute seamlessly; state-changing or shell-operator commands require explicit natural language staging and user confirmation.
- **⚙️ Pure Native macOS System Controls:** 
  Native volume control, dark mode toggling, screen lock, native notification banners, and non-blocking countdown timers with zero external heavyweight packages.

---

## 🏛 Architecture

```
User Input
    │
    ▼
[ Situational Detector ] ── (driving / meeting / desk / default)
    │
    ▼
[ Rule-Based Fast Planner ] ──(found)──► [ Task Queue (FIFO) ]
    │ (not found)                               │
    ▼                                           ▼
[ Power-Throttled AI Planner ] ────────► [ Executor ]
    │ (conversational)                          │
    ▼                                           ▼
[ LLM Chat Session ]                   [ Tool Manager ]
                                                │
         ┌──────────────┬──────────────┬────────┴─────────────┬──────────────┐
         ▼              ▼              ▼                      ▼              ▼
    [ System ]     [ Terminal ]    [ Perception ]      [ Notification ]  [ Browser/Files ]
  (Audio/Power)   (Policy Sandboxed) (Multimodal)      (Timers/Banners)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- macOS 12+ (Apple Silicon recommended)
- Python 3.10+
- Optional: [Ollama](https://ollama.com) running locally for offline neural planning (`ollama run gemma3:4b` or `ollama run llava`)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/edith.git
cd edith

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (lightweight core)
pip install -r reqirements.txt
```

### 3. Launching EDITH
```bash
./edith.sh
# or directly:
python src/app.py
```

---

## 🕹 Example Commands

```text
# System & Hardware
EDITH > check battery
EDITH > set volume 60%
EDITH > toggle dark mode
EDITH > lock screen

# Situational Output Modes
EDITH > /mode driving
EDITH > /mode meeting
EDITH > /mode desk

# Multimodal Screen Understanding
EDITH > what is on my screen
EDITH > explain the error on my screen

# Reminders & Timers
EDITH > set a timer for 15 minutes
EDITH > remind me in 10 minutes to review the pull request
EDITH > /timers

# Power & Battery Management
EDITH > /power
EDITH > /eco on
```

---

## 🧪 Testing & Verification

EDITH adheres strictly to test-driven contracts: Every skill returns structured `ActionResult` objects, respects FIFO queue sequencing, and executes deterministic actions without raw string leaks.

Run the test suite:
```bash
source venv/bin/activate
python -m unittest discover -s tests -v
```
**Test Status:** 117 automated unit tests passing in `< 0.1s`.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
