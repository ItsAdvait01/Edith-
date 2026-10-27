from core.llm import LLM
from core.chat import ChatSession
from commands.commands import Commands
from memory.memory_manager import MemoryManager
from tools.tool_manager import ToolManager
from brain.planner import Planner
from brain.ai_planner import AIPlanner
from brain.executor import Executor
from brain.task_queue import TaskQueue
from brain.task_history import TaskHistory
from context.context_manager import ContextManager
from context.situation_detector import SituationDetector
from security.confirmation_manager import ConfirmationManager
from security.audit_logger import AuditLogger
from memory.memory_store import MemoryStore
from voice.voice_engine import VoiceEngine
from voice.output_router import OutputRouter, RenderOutput
from voice.voice_personality import VoicePersonality
from system.power_manager import PowerManager


def main():

    # Initialize components
    brain = LLM()
    chat = ChatSession()
    memory_store = MemoryStore()
    voice_engine = VoiceEngine()
    power_manager = PowerManager()
    situation_detector = SituationDetector()
    tool_manager = ToolManager(memory_store=memory_store, voice_engine=voice_engine, llm=brain)
    task_queue = TaskQueue()
    task_history = TaskHistory()
    context_manager = ContextManager()
    audit_logger = AuditLogger()
    capabilities = {
        capability["name"]: capability
        for capability in tool_manager.get_capabilities()
    }
    planner = Planner(task_queue, capabilities, context_manager)
    ai_planner = AIPlanner(capabilities=capabilities, llm=brain)
    executor = Executor(task_queue, tool_manager, task_history, audit_logger)
    confirmation_manager = ConfirmationManager()
    output_router = OutputRouter()
    voice_personality = VoicePersonality(memory_store=memory_store)
    voice_state = {"enabled": False}  # Voice off by default
    
    print("=" * 35)
    print("EDITH v0.0.2")
    print("=" * 35)

    _format_pending_tasks(task_queue)
    initial_greeting = voice_personality.get_greeting()
    power_status = power_manager.get_power_status()
    if power_status.get("is_on_battery"):
        initial_greeting += f" (⚡ Battery: {power_status['percentage']}% — Eco intelligence active.)"
    print(f"\nEDITH > {initial_greeting}")
    
    while True:

        user_input = input("\nYou > ").strip()

        if not user_input:
            continue
            
        # The prompt is only used for the chat/LLM history, 
        # so don't record confirmation prompts
        if not Planner.is_confirmation(user_input) and not Commands.is_command(user_input):
            # Record it manually if executing from queue?
            pass

        # Power & Battery Commands (Battery-Aware Intelligence)
        if user_input.lower() in ["/power", "/eco"]:
            summary = power_manager.get_summary()
            print(f"\nEDITH > {summary}")
            if voice_state["enabled"]:
                voice_engine.speak(summary)
            continue

        if user_input.lower() in ["/eco on", "/eco enable"]:
            power_manager.set_manual_profile("eco")
            msg = "Eco Saver mode enabled. Heavy local inference throttled to protect battery."
            print(f"\nEDITH > {msg}")
            if voice_state["enabled"]:
                voice_engine.speak(msg)
            continue

        if user_input.lower() in ["/eco off", "/eco disable"]:
            power_manager.set_manual_profile("auto")
            msg = "Eco Saver mode disabled. Returning to auto power management."
            print(f"\nEDITH > {msg}")
            if voice_state["enabled"]:
                voice_engine.speak(msg)
            continue

        # Situational Output Mode (Sprint 21.1)
        import re as _re
        _mode_input = user_input.strip().lower()
        if _mode_input in ["/mode", "output mode", "current mode", "what mode"]:
            print(f"\nEDITH >\n{situation_detector.get_summary()}")
            if voice_state["enabled"]:
                voice_engine.speak(f"Output mode is {situation_detector.mode}.")
            continue

        _mode_match = _re.match(
            r"^(?:/mode\s+|(?:switch to |set mode |i am |i'm |)(driving|desk|meeting|default)(?: mode)?)$",
            _mode_input
        )
        if _mode_match:
            new_mode = _mode_match.group(1)
            situation_detector.set_mode(new_mode)
            icons = {"driving": "🚗", "desk": "🖥", "meeting": "🤫", "default": "⚡"}
            icon = icons.get(new_mode, "")
            msg = f"Switched to {icon} {new_mode.capitalize()} mode."
            print(f"\nEDITH > {msg}")
            if voice_state["enabled"]:
                voice_engine.speak(msg)
            continue

        # Execution Queue commands take precedence
        if user_input.lower() in ["/queue"]:
            print(_format_pending_tasks(task_queue))
            continue

        if user_input.lower().startswith("/cancel "):
            try:
                position = int(user_input[8:].strip())
                if task_queue.cancel(position):
                    print(f"\nEDITH > Cancelled task at position {position}.")
                else:
                    print(f"\nEDITH > No pending task at position {position}.")
            except ValueError:
                print("\nEDITH > Invalid position.")
            continue
            
        if user_input.lower() in ["/clear-queue"]:
            task_queue.clear()
            print("\nEDITH > Cleared all pending tasks.")
            continue
            
        if user_input.lower() in ["/failed"]:
            print(_format_failed_tasks(task_queue))
            continue
            
        if user_input.lower().startswith("/retry "):
            try:
                position = int(user_input[7:].strip())
                msg, success = _retry_task(task_queue, position)
                print(msg)
                if success:
                    results = _execute_and_display_queue(
                        executor, task_queue, confirmation_manager,
                        voice_engine=voice_engine,
                        voice_personality=voice_personality,
                        voice_state=voice_state,
                        situation_detector=situation_detector,
                    )
            except ValueError:
                print("\nEDITH > Invalid position.")
            continue
            
        if user_input.lower().startswith("/confirm "):
            try:
                position = int(user_input[9:].strip())
                msg, success = _confirm_task(task_queue, position)
                print(msg)
                if success:
                    results = _execute_and_display_queue(
                        executor, task_queue, confirmation_manager,
                        voice_engine=voice_engine,
                        voice_personality=voice_personality,
                        voice_state=voice_state,
                        situation_detector=situation_detector,
                    )
            except ValueError:
                print("\nEDITH > Invalid position.")
            continue

        if user_input.lower() in ["/context"]:
            result = _get_active_context()
            print(f"\nEDITH > {result.message}")
            if voice_state["enabled"]:
                voice_engine.speak(result.message)
            continue

        # Active window / context (OS-level, not vision) 
        if user_input.lower() in [
            "what am i working on", "what am i working on?",
            "what is my active window", "what is my active window?",
            "what is my context", "what is my context?"
        ]:
            result = _get_active_context()
            print(f"\nEDITH > {result.message}")
            if voice_state["enabled"]:
                voice_engine.speak(result.message)
            continue

        if user_input.lower() in [
            "what is in my clipboard", "what is in my clipboard?",
            "what's in my clipboard", "what's in my clipboard?",
            "what did i copy", "what did i copy?"
        ]:
            clip_res = context_manager.get_clipboard()
            msg = clip_res.message
            print(f"\nEDITH > {msg}")
            if voice_state["enabled"]:
                voice_engine.speak(msg)
            continue
            
        if user_input.lower() in ["/history"]:
            print(_format_task_history(task_history))
            continue

        # Confirmation Manager (Sprint 12.1)
        if confirmation_manager.has_pending and Planner.is_confirmation(user_input):
            task = confirmation_manager.confirm_staged()

            task_queue.retry_failed_task(task)
            print(f"\nEDITH > Confirmed {task.tool}:{task.action} {task.target}.")
            results = _execute_and_display_queue(
                executor, task_queue, confirmation_manager,
                voice_engine=voice_engine,
                voice_personality=voice_personality,
                voice_state=voice_state,
                situation_detector=situation_detector,
            )
            continue

        # Any non-confirmation input cancels a stale staged task
        if confirmation_manager.has_pending:
            confirmation_manager.cancel_staged()

        # Slash Commands
        if Commands.is_command(user_input):

            if Commands.execute(
                user_input, chat, brain,
                voice_state=voice_state,
                personality=voice_personality,
                voice_engine=voice_engine
            ):
                continue

        tasks = planner.plan(user_input)

        if tasks:
            
            # Use the streaming task status (Sprint 15.2)
            results = _execute_and_display_queue(
                executor, task_queue, confirmation_manager,
                voice_engine=voice_engine,
                voice_personality=voice_personality,
                voice_state=voice_state,
                situation_detector=situation_detector,
            )
            tool_result = "\n".join(result.message for result in results)
            chat.add_user(user_input)
            chat.add_assistant(tool_result)
            continue

        # Pre-response acknowledgment cue before AI planning / Chat generation (Sprint 18.1)
        if voice_state["enabled"]:
            voice_engine.speak(voice_personality.get_acknowledgment(), rate=VoicePersonality.RATE_FAST)

        # Sprint 16.0 / Battery-Aware Intelligence:
        # AI planner fallback — throttled on battery for conversational queries to prevent M1 heat
        ai_tasks = []
        if not power_manager.should_throttle_speculative_ai(user_input):
            ai_tasks = ai_planner.plan(user_input)
        if ai_tasks:
            for task in ai_tasks:
                task_queue.enqueue(task)

            results = _execute_and_display_queue(
                executor, task_queue, confirmation_manager,
                voice_engine=voice_engine,
                voice_personality=voice_personality,
                voice_state=voice_state,
                situation_detector=situation_detector,
            )
            tool_result = "\n".join(result.message for result in results)
            chat.add_user(user_input)
            chat.add_assistant(tool_result)
            continue

        # Exit
        if user_input.lower() in ["exit", "/exit"]:
            print("\nGoodbye 👋")
            break

        # Add user message
        chat.add_user(user_input)

        print("\nEDITH > ", end="", flush=True)

        # Get LLM response with JARVIS personality guidelines and user context
        messages = _build_chat_messages(chat, memory_store=memory_store)
        reply = brain.ask_stream(messages)

        # Dual-Channel Voice output (Sprint 18.1)
        if voice_state["enabled"] and reply:
            if output_router.is_theory_or_explanation(reply, user_input):
                spoken = output_router.format_spoken_explanation(reply)
                voice_engine.speak(spoken)
            else:
                mode = output_router.classify(reply)
                if mode == "speak":
                    spoken = output_router.format_spoken_sentence(reply)
                    voice_engine.speak(spoken)
                else:
                    notice = output_router.get_spoken_notice(reply)
                    voice_engine.speak(notice)

        # Store assistant reply
        chat.add_assistant(reply)


def _build_chat_messages(chat, memory_store=None):
    """Build messages payload with F.R.I.D.A.Y. adaptive system instructions and memory context."""
    user_name = None
    if memory_store:
        for k in ["my name", "name", "user_name"]:
            val = memory_store.get(k)
            if val:
                user_name = str(val).strip()
                break

    name_instruction = f" The user's name is {user_name}. You can address them by name or as Boss." if user_name else " You can address the user as Boss."

    system_prompt = (
        f"You are EDITH, operating with the persona, tactical efficiency, warmth, and loyalty of F.R.I.D.A.Y. from the Marvel Cinematic Universe.{name_instruction}\n\n"
        "Dynamic Tone & Adaptive Style:\n"
        "- Auto-shift your tone to match the user's vibe and context:\n"
        "  * Casual & Friendly Mode: When the user is casual, conversational, joking, or talking informally (e.g. 'yo', 'hey', 'bro', 'what's up'), match their energy! Be witty, warm, and playful. Feel free to sprinkle in natural conversational slang ('gotchu', 'no sweat', 'piece of cake', 'let's roll', 'you got it') and charming, dry F.R.I.D.A.Y. humor.\n"
        "  * Formal & Tactical Mode: When the user is working on serious architecture, system tasks, critical debugging, or safety confirmations, seamlessly shift to a crisp, sharp, professional, and tactical tone with direct clarity and zero fluff.\n\n"
        "Critical Rule on When to Provide Code:\n"
        "- NEVER output code blocks unless the user explicitly requests code, a script, or a programming solution. For general questions, greetings ('how are you', 'what's up'), or non-technical queries, respond purely conversationally without generating unsolicited code.\n\n"
        "Code & Theory Explanation Guidelines:\n"
        "1. Standard Code Gist (when providing code snippets without an explicit request for theory):\n"
        "   - Whenever you provide code, always precede or accompany it with a short, clear 1-2 sentence gist explaining what the code does and its overall logic so the user immediately grasps it.\n"
        "   - If the code has multiple or large steps, explain each step clearly.\n"
        "   - If the code is short, provide a full, clear explanation of how it works.\n"
        "   - If the code or concept is long or tricky, keep the explanation simple, intuitive, and concise without overcomplicating.\n"
        "2. Theory & Conceptual Explanation Pattern (MANDATORY for all theory, algorithm, concept, or 'explain' questions, e.g. 'explain how binary search works', 'how does X work', 'explain...'):\n"
        "   - In all theory, algorithm, or explanation questions, ALWAYS structure your response with these exact descriptive sections in this order:\n"
        "     * Purpose: What problem it solves and why it is used.\n"
        "     * Key Components: Core building blocks, logic, or algorithmic mechanics.\n"
        "     * Input: What inputs, types, structures, and prerequisites are expected (e.g. sorted list).\n"
        "     * Output: What format, return value, or result is produced.\n"
        "     * Common Errors & Pitfalls: Common runtime, logic, or edge-case errors (e.g., off-by-one, infinite loops) and how to prevent them.\n"
        "     * Examples: A clear, descriptive walkthrough with concrete examples illustrating the concept in action (with code if applicable).\n"
        "     * Interactive Check: Always close with an interactive check to see if they understood, if they'd like you to clarify or repeat anything, or if they have any other questions.\n"
        "   - Keep this pattern in most theory questions so the explanation can be spoken descriptively and thoroughly.\n"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat.get_history())
    return messages

        
def _format_pending_tasks(task_queue):
    if task_queue.is_empty():
        return "\nEDITH > No pending tasks."

    lines = ["\nEDITH > Pending tasks:"]

    for position, task in enumerate(task_queue.pending_tasks, start=1):
        lines.append(f"{position}. {task.tool}:{task.action} {task.target}")

    return "\n".join(lines)


def _cancel_pending_task(task_queue, position_text):
    try:
        position = int(position_text)
    except ValueError:
        return "\nEDITH > Use /cancel followed by a queue position, for example: /cancel 1"

    task = task_queue.cancel_position(position)

    if task is None:
        return "\nEDITH > No pending task exists at that position."

    return f"\nEDITH > Cancelled {task.tool}:{task.action} {task.target}."


def _format_failed_tasks(task_queue):
    if not task_queue.failed_task_snapshot:
        return "\nEDITH > No failed tasks."

    lines = ["\nEDITH > Failed tasks:"]

    for position, task in enumerate(task_queue.failed_task_snapshot, start=1):
        lines.append(
            f"{position}. {task.tool}:{task.action} {task.target} "
            f"(attempts: {task_queue.attempts(task)})"
        )

    return "\n".join(lines)


def _retry_failed_task(task_queue, position_text):
    try:
        position = int(position_text)
    except ValueError:
        return "\nEDITH > Use /retry followed by a failed-task position, for example: /retry 1"

    task = task_queue.retry_failed_position(position)

    if task is None:
        return "\nEDITH > No failed task exists at that position."

    return f"\nEDITH > Requeued {task.tool}:{task.action} {task.target}."


def _confirm_failed_task(task_queue, confirmation_manager, position_text):
    try:
        position = int(position_text)
    except ValueError:
        return (
            "\nEDITH > Use /confirm followed by a failed-task position, for example: /confirm 1",
            False,
        )

    if position < 1 or position > len(task_queue.failed_task_snapshot):
        return "\nEDITH > No failed task exists at that position.", False

    task = task_queue.failed_task_snapshot[position - 1]
    confirmation_manager.confirm(task)
    task_queue.retry_failed_position(position)
    return f"\nEDITH > Confirmed and requeued {task.tool}:{task.action} {task.target}.", True


def _execute_and_display_queue(
    executor, task_queue, confirmation_manager,
    voice_engine=None, voice_personality=None, voice_state=None,
    situation_detector=None,
):
    """Execute tasks with real-time visible status and situational adaptive output (Sprint 21.1)."""
    results = []

    while not task_queue.is_empty():
        task = task_queue.pending_tasks[0]
        print(f"\n⚙️  Running {task.tool}:{task.action} '{task.target}'...")

        result = executor.execute_next()
        results.append(result)

        if result.success:
            mode = situation_detector.mode if situation_detector else "default"
            render = OutputRouter.render_for_mode(
                mode,
                action_result=result,
                response_text=result.message,
            )

            # ── Screen ────────────────────────────────────────────────
            if render.screen is not None:
                print(f"\n{render.screen}")
            else:
                # Minimal indicator (driving: eyes on road, no rich card)
                print(f"✅ {result.message}")

            # ── Voice ─────────────────────────────────────────────────
            if voice_state and voice_state.get("enabled") and voice_engine:
                if render.voice:
                    voice_engine.speak(render.voice)
                if render.follow_up:
                    voice_engine.speak(render.follow_up)
        else:
            print(f"❌ {result.message}")

        # Stage any task that needs confirmation (Sprint 12.1)
        if result.error == "confirmation_required" and result.data:
            for failed_task in task_queue.failed_task_snapshot:
                if failed_task.target == result.data.get("command"):
                    confirmation_manager.stage(failed_task)
                    break

            # Voice confirmation dialogue (Sprint 18.1)
            if voice_state and voice_state.get("enabled") and voice_engine and voice_personality:
                risk = "high"
                if result.metadata and isinstance(result.metadata, dict):
                    risk = result.metadata.get("risk_level", "high")
                notice = voice_personality.get_confirmation_notice(risk_level=risk)
                voice_engine.speak(notice, rate=voice_personality.RATE_DELIBERATE)

        if not result.success:
            break

    return results


def _get_active_context():
    # Import and instantiate only for the explicit /context request.
    from context.context_manager import ContextManager

    return ContextManager().get_active_context()


def _format_task_history(task_history):
    entries = task_history.entries
    if not entries:
        return "\nEDITH > No task history."

    lines = ["\nEDITH > Task History:"]
    for i, entry in enumerate(entries, start=1):
        status = "✅" if entry["success"] else "❌"
        lines.append(f"{i}. {status} {entry['task']} - {entry['message']}")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
