import sys
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from brain.executor import Executor
from brain.action_result import ActionResult
from brain.planner import Planner
from brain.task import Task
from brain.task_queue import TaskQueue
from brain.task_history import TaskHistory
from context.context_manager import ContextManager
from security.confirmation_manager import ConfirmationManager
from tools.tool_manager import ToolManager
from tools.terminal_tool import TerminalTool
from tools.browser_tool import BrowserTool
from security.command_policy import CommandPolicy


class RecordingToolManager(ToolManager):
    def __init__(self):
        self.received_tasks = []

    def execute(self, task):
        self.received_tasks.append(task)
        return ActionResult(
            success=True,
            message=f"executed:{task.tool}:{task.action}:{task.target}",
        )


class StructuredExecutionTests(unittest.TestCase):
    def test_task_defaults_support_future_execution_metadata(self):
        task = Task(tool="app", action="open", target="chrome")

        self.assertEqual(task.parameters, {})
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.status, "pending")

    def test_executor_passes_structured_task_to_tool_manager(self):
        manager = RecordingToolManager()
        task = Task(tool="app", action="open", target="chrome")

        task_queue = TaskQueue()
        task_queue.enqueue(task)

        results = Executor(task_queue, manager).execute_all()

        self.assertEqual(manager.received_tasks, [task])
        self.assertEqual(results[0].message, "executed:app:open:chrome")
        self.assertTrue(results[0].success)

    def test_planner_enqueues_tasks_when_given_a_task_queue(self):
        task_queue = TaskQueue()
        tasks = Planner(task_queue).plan("open chrome")

        self.assertEqual(task_queue.peek(), tasks[0])
        self.assertEqual(tasks[0].status, TaskQueue.PENDING)

    def test_planner_creates_and_enqueues_multiple_ordered_app_tasks(self):
        task_queue = TaskQueue()
        capabilities = {
            item["name"]: item
            for item in ToolManager().get_capabilities()
        }

        tasks = Planner(task_queue, capabilities).plan("open chrome and vscode")

        self.assertEqual([task.target for task in tasks], ["chrome", "vscode"])
        self.assertEqual(
            [task.target for task in task_queue.pending_tasks],
            ["chrome", "vscode"],
        )

    def test_planner_creates_a_python_project_workflow(self):
        task_queue = TaskQueue()
        capabilities = {item["name"]: item for item in ToolManager().get_capabilities()}

        tasks = Planner(task_queue, capabilities).plan("create Python project called VisionAI")

        self.assertEqual(
            [(task.action, task.target) for task in tasks],
            [
                ("create_folder", "VisionAI"),
                ("create_file", "VisionAI/README.md"),
                ("create_file", "VisionAI/main.py"),
            ],
        )
        self.assertEqual(task_queue.pending_tasks, tuple(tasks))

    def test_task_queue_preserves_order_and_tracks_lifecycle(self):
        first_task = Task(tool="app", action="open", target="chrome")
        second_task = Task(tool="file", action="create_folder", target="AI")
        task_queue = TaskQueue()

        task_queue.enqueue(first_task)
        task_queue.enqueue(second_task)

        self.assertEqual(task_queue.peek(), first_task)
        self.assertEqual(task_queue.dequeue(), first_task)
        self.assertEqual(first_task.status, TaskQueue.RUNNING)
        task_queue.mark_completed(first_task)

        self.assertEqual(task_queue.dequeue(), second_task)
        task_queue.mark_failed(second_task)

        self.assertEqual(first_task.status, TaskQueue.COMPLETED)
        self.assertEqual(second_task.status, TaskQueue.FAILED)
        self.assertEqual(task_queue.completed_tasks, [first_task])
        self.assertEqual(task_queue.failed_tasks, [second_task])
        self.assertTrue(task_queue.is_empty())

    def test_task_queue_cancel_and_clear_only_cancel_pending_tasks(self):
        first_task = Task(tool="app", action="open", target="chrome")
        second_task = Task(tool="app", action="open", target="safari")
        task_queue = TaskQueue()

        task_queue.enqueue(first_task)
        task_queue.enqueue(second_task)

        self.assertTrue(task_queue.cancel(first_task))
        task_queue.clear()

        self.assertEqual(first_task.status, TaskQueue.CANCELLED)
        self.assertEqual(second_task.status, TaskQueue.CANCELLED)
        self.assertEqual(task_queue.cancelled_tasks, [first_task, second_task])
        self.assertTrue(task_queue.is_empty())

    def test_task_queue_cancels_a_task_by_one_based_position(self):
        first_task = Task(tool="app", action="open", target="chrome")
        second_task = Task(tool="app", action="open", target="safari")
        task_queue = TaskQueue()

        task_queue.enqueue(first_task)
        task_queue.enqueue(second_task)

        self.assertEqual(task_queue.cancel_position(2), second_task)
        self.assertEqual(second_task.status, TaskQueue.CANCELLED)
        self.assertEqual(task_queue.pending_tasks, (first_task,))
        self.assertIsNone(task_queue.cancel_position(2))

    def test_executor_stops_after_a_failed_task_and_preserves_remaining_work(self):
        class FailingToolManager:
            def __init__(self):
                self.executed_targets = []

            def execute(self, task):
                self.executed_targets.append(task.target)
                return ActionResult(
                    success=task.target != "broken",
                    message=task.target,
                    error="simulated_failure" if task.target == "broken" else None,
                )

        task_queue = TaskQueue()
        task_queue.enqueue(Task(tool="app", action="open", target="broken"))
        task_queue.enqueue(Task(tool="app", action="open", target="chrome"))
        manager = FailingToolManager()

        results = Executor(task_queue, manager).execute_all()

        self.assertEqual([result.message for result in results], ["broken"])
        self.assertEqual(manager.executed_targets, ["broken"])
        self.assertEqual(task_queue.peek().target, "chrome")
        self.assertEqual(task_queue.peek().status, TaskQueue.PENDING)

    def test_failed_task_can_be_requeued_and_retried(self):
        class RecoveringToolManager:
            def __init__(self):
                self.calls = 0

            def execute(self, task):
                self.calls += 1
                return ActionResult(
                    success=self.calls > 1,
                    message="recovered" if self.calls > 1 else "failed",
                    error=None if self.calls > 1 else "temporary_failure",
                )

        task = Task(tool="app", action="open", target="chrome")
        task_queue = TaskQueue()
        task_queue.enqueue(task)
        manager = RecoveringToolManager()
        executor = Executor(task_queue, manager)

        first_result = executor.execute_next()
        self.assertFalse(first_result.success)
        self.assertEqual(task_queue.attempts(task), 1)
        self.assertEqual(task_queue.retry_failed_position(1), task)
        self.assertEqual(task.status, TaskQueue.PENDING)

        second_result = executor.execute_next()
        self.assertTrue(second_result.success)
        self.assertEqual(task_queue.attempts(task), 2)
        self.assertEqual(task.status, TaskQueue.COMPLETED)

    def test_retried_task_is_placed_ahead_of_later_pending_work(self):
        failed_task = Task(tool="app", action="open", target="chrome")
        pending_task = Task(tool="app", action="open", target="vscode")
        task_queue = TaskQueue()

        task_queue.enqueue(failed_task)
        task_queue.enqueue(pending_task)
        task_queue.dequeue()
        task_queue.mark_failed(failed_task)

        task_queue.retry_failed_position(1)

        self.assertEqual(task_queue.pending_tasks, (failed_task, pending_task))

    def test_planner_creates_structured_file_task(self):
        tasks = Planner().plan("create folder AI")

        self.assertEqual(tasks, [Task(tool="file", action="create_folder", target="AI")])

    def test_tool_manager_executes_folder_task_without_text_reparsing(self):
        original_directory = os.getcwd()

        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                result = ToolManager().execute(
                    Task(tool="file", action="create_folder", target="AI")
                )
            finally:
                os.chdir(original_directory)

            self.assertIsInstance(result, ActionResult)
            self.assertTrue(result.success)
            self.assertEqual(result.message, "Folder 'AI' created successfully.")
            self.assertGreaterEqual(result.execution_time, 0)
            self.assertTrue(Path(temporary_directory, "AI").is_dir())

    def test_tool_manager_registers_every_skill_by_its_name(self):
        manager = ToolManager()

        self.assertEqual(
            set(manager.tools_by_name),
            {"app", "calculator", "datetime", "file", "terminal", "browser", "memory", "perception", "system", "notification"},
        )

    def test_skill_metadata_is_discoverable_without_execution(self):
        manager = ToolManager()

        capabilities = {item["name"]: item for item in manager.get_capabilities()}

        self.assertEqual(
            set(capabilities),
            {"app", "calculator", "datetime", "file", "terminal", "browser", "memory", "perception", "system", "notification"},
        )
        self.assertEqual(capabilities["app"]["supported_actions"], ("open",))
        self.assertEqual(capabilities["file"]["resource_profile"], "file_system")
        self.assertEqual(capabilities["system"]["resource_profile"], "device")
        self.assertIn("battery_status", capabilities["system"]["supported_actions"])
        self.assertEqual(capabilities["notification"]["resource_profile"], "on_demand")
        self.assertIn("set_timer", capabilities["notification"]["supported_actions"])
        self.assertEqual(
            manager.get_skill_metadata("calculator")["description"],
            "Evaluates a calculator expression.",
        )
        self.assertEqual(
            capabilities["terminal"]["supported_actions"],
            ("execute",),
        )
        self.assertIsNone(manager.get_skill_metadata("missing"))

    def test_legacy_file_commands_still_work_through_the_task_adapter(self):
        original_directory = os.getcwd()

        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                manager = ToolManager()
                self.assertEqual(
                    manager.process("create file notes.txt").message,
                    "File 'notes.txt' created successfully.",
                )
                self.assertEqual(manager.process("list").message, "notes.txt")
                self.assertEqual(manager.process("delete notes.txt").message, "notes.txt deleted.")
            finally:
                os.chdir(original_directory)

    def test_calculator_and_datetime_accept_structured_tasks(self):
        manager = ToolManager()

        calculator_result = manager.execute(
            Task(tool="calculator", action="calculate", target="2 + 2")
        )
        self.assertTrue(calculator_result.success)
        self.assertEqual(calculator_result.message, "4")

        time_result = manager.execute(Task(tool="datetime", action="get_time"))
        self.assertTrue(time_result.success)
        self.assertRegex(
            time_result.message,
            r"\d{2}:\d{2}:\d{2} (AM|PM)",
        )

    def test_failed_skill_execution_also_returns_action_result(self):
        task = Task(tool="app", action="open", target="unknown app")
        task_queue = TaskQueue()
        task_queue.enqueue(task)

        result = Executor(task_queue, ToolManager()).execute_next()

        self.assertIsInstance(result, ActionResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error, "unknown_app")
        self.assertEqual(task.status, "failed")

    def test_context_manager_reads_active_context_on_demand(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(stdout="Google Chrome|New Tab\n")

        result = ContextManager(command_runner=runner).get_active_context()

        self.assertTrue(result.success)
        self.assertEqual(result.data, {"application": "Google Chrome", "window_title": "New Tab"})
        self.assertTrue(result.metadata["on_demand"])

    def test_context_manager_returns_action_result_when_macos_context_fails(self):
        def failing_runner(*args, **kwargs):
            raise RuntimeError("Accessibility access is unavailable")

        result = ContextManager(command_runner=failing_runner).get_active_context()

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Unable to read active macOS context.")
        self.assertIn("Accessibility access", result.error)

    def test_terminal_runs_read_only_command_without_confirmation(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(returncode=0, stdout="/tmp\n", stderr="")

        result = TerminalTool(command_runner=runner).execute(
            Task(tool="terminal", action="execute", target="pwd")
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "/tmp")
        self.assertFalse(result.metadata["requires_confirmation"])

    def test_terminal_requires_confirmation_for_a_state_changing_command(self):
        task = Task(tool="terminal", action="execute", target="mkdir demo")
        tool = TerminalTool()

        result = tool.execute(task)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "confirmation_required")

    def test_terminal_requires_confirmation_for_chained_shell_command(self):
        task = Task(tool="terminal", action="execute", target="pwd; mkdir demo")

        result = TerminalTool().execute(task)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "confirmation_required")

    def test_confirmed_terminal_task_runs_through_queue(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(returncode=0, stdout="created\n", stderr="")

        task = Task(tool="terminal", action="execute", target="mkdir demo")
        task_queue = TaskQueue()
        task_queue.enqueue(task)
        tool_manager = type(
            "TerminalManager",
            (),
            {"execute": lambda self, current_task: TerminalTool(runner).execute(current_task)},
        )()
        executor = Executor(task_queue, tool_manager)

        first_result = executor.execute_next()
        self.assertEqual(first_result.error, "confirmation_required")
        ConfirmationManager().confirm(task)
        task_queue.retry_failed_position(1)
        second_result = executor.execute_next()

        self.assertTrue(second_result.success)
        self.assertEqual(second_result.message, "created")
        self.assertEqual(task.status, TaskQueue.COMPLETED)

    @patch("tools.app_launcher.subprocess.run")
    def test_legacy_process_is_a_compatibility_adapter(self, run_application):
        task = Task(tool="app", action="open", target="chrome")
        manager = ToolManager()

        result = manager.process("open chrome")

        self.assertIsInstance(result, ActionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Opening Google Chrome...")
        run_application.assert_called_once_with(
            ["open", "-a", "Google Chrome"],
            check=True,
        )

        # The direct, structured path is the same task contract.
        with patch("tools.app_launcher.subprocess.run") as direct_run:
            direct_result = manager.execute(task)

        self.assertIsInstance(direct_result, ActionResult)
        self.assertTrue(direct_result.success)
        self.assertEqual(direct_result.message, "Opening Google Chrome...")
        direct_run.assert_called_once_with(
            ["open", "-a", "Google Chrome"],
            check=True,
        )

    # --- Sprint 12.1: Natural-language confirmation tests ---

    def test_confirmation_manager_stages_and_confirms_a_task(self):
        task = Task(tool="terminal", action="execute", target="mkdir demo")
        manager = ConfirmationManager()

        manager.stage(task)

        self.assertTrue(manager.has_pending)
        self.assertIs(manager.pending_task, task)

        confirmed = manager.confirm_staged()

        self.assertIs(confirmed, task)
        self.assertTrue(task.parameters["confirmed"])
        self.assertFalse(manager.has_pending)
        self.assertIsNone(manager.pending_task)

    def test_confirmation_manager_cancel_clears_staged_task(self):
        task = Task(tool="terminal", action="execute", target="rm -rf /")
        manager = ConfirmationManager()

        manager.stage(task)
        cancelled = manager.cancel_staged()

        self.assertIs(cancelled, task)
        self.assertFalse(manager.has_pending)
        self.assertNotIn("confirmed", task.parameters)

    def test_confirmation_manager_replaces_staged_task(self):
        task_a = Task(tool="terminal", action="execute", target="mkdir a")
        task_b = Task(tool="terminal", action="execute", target="mkdir b")
        manager = ConfirmationManager()

        manager.stage(task_a)
        manager.stage(task_b)

        self.assertIs(manager.pending_task, task_b)
        self.assertFalse(manager.has_pending and manager.pending_task is task_a)

    def test_planner_recognizes_confirmation_phrases(self):
        self.assertTrue(Planner.is_confirmation("yes"))
        self.assertTrue(Planner.is_confirmation("y"))
        self.assertTrue(Planner.is_confirmation("confirm"))
        self.assertTrue(Planner.is_confirmation("  YES  "))
        self.assertTrue(Planner.is_confirmation("  Y  "))

        self.assertFalse(Planner.is_confirmation("yes run"))
        self.assertFalse(Planner.is_confirmation("yep"))
        self.assertFalse(Planner.is_confirmation("yeah"))
        self.assertFalse(Planner.is_confirmation("open chrome"))
        self.assertFalse(Planner.is_confirmation(""))

    def test_natural_language_confirmation_runs_staged_task(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(returncode=0, stdout="created\n", stderr="")

        task = Task(tool="terminal", action="execute", target="mkdir demo")
        task_queue = TaskQueue()
        task_queue.enqueue(task)
        tool_manager = type(
            "TerminalManager",
            (),
            {"execute": lambda self, t: TerminalTool(runner).execute(t)},
        )()
        executor = Executor(task_queue, tool_manager)
        confirmation_manager = ConfirmationManager()

        # First execution: confirmation_required
        first_result = executor.execute_next()
        self.assertEqual(first_result.error, "confirmation_required")

        # Stage the failed task
        confirmation_manager.stage(task)

        # Simulate natural-language "yes"
        self.assertTrue(Planner.is_confirmation("yes"))
        self.assertTrue(confirmation_manager.has_pending)

        confirmed_task = confirmation_manager.confirm_staged()
        self.assertTrue(confirmed_task.parameters["confirmed"])

        task_queue.retry_failed_position(1)
        second_result = executor.execute_next()

        self.assertTrue(second_result.success)
        self.assertEqual(second_result.message, "created")
        self.assertEqual(task.status, TaskQueue.COMPLETED)

    # --- Sprint 12.2: Command policy tests ---

    def test_command_policy_classifies_read_only_as_none(self):
        policy = CommandPolicy()

        self.assertEqual(policy.classify("pwd"), CommandPolicy.RISK_NONE)
        self.assertEqual(policy.classify("ls"), CommandPolicy.RISK_NONE)
        self.assertEqual(policy.classify("cat file.txt"), CommandPolicy.RISK_NONE)
        self.assertEqual(policy.classify("git status"), CommandPolicy.RISK_NONE)
        self.assertEqual(policy.classify("git diff"), CommandPolicy.RISK_NONE)
        self.assertEqual(policy.classify("echo hello"), CommandPolicy.RISK_NONE)

        self.assertFalse(policy.requires_confirmation("pwd"))
        self.assertFalse(policy.requires_confirmation("ls"))

    def test_command_policy_classifies_destructive_commands(self):
        policy = CommandPolicy()

        self.assertEqual(policy.classify("rm -rf /"), CommandPolicy.RISK_DESTRUCTIVE)
        self.assertEqual(policy.classify("kill 1234"), CommandPolicy.RISK_DESTRUCTIVE)
        self.assertEqual(policy.classify("killall python"), CommandPolicy.RISK_DESTRUCTIVE)
        self.assertEqual(policy.classify("shutdown"), CommandPolicy.RISK_DESTRUCTIVE)
        self.assertEqual(policy.classify("rmdir old"), CommandPolicy.RISK_DESTRUCTIVE)

        self.assertTrue(policy.requires_confirmation("rm file.txt"))

    def test_command_policy_classifies_shell_operators_as_high(self):
        policy = CommandPolicy()

        self.assertEqual(policy.classify("pwd; rm -rf /"), CommandPolicy.RISK_HIGH)
        self.assertEqual(policy.classify("echo a | cat"), CommandPolicy.RISK_HIGH)
        self.assertEqual(policy.classify("cat $(whoami)"), CommandPolicy.RISK_HIGH)
        self.assertEqual(policy.classify("ls > out.txt"), CommandPolicy.RISK_HIGH)

        self.assertTrue(policy.requires_confirmation("pwd; rm -rf /"))

    def test_command_policy_format_preview_includes_risk_and_directory(self):
        policy = CommandPolicy()
        preview = policy.format_preview("mkdir demo", CommandPolicy.RISK_HIGH, "/tmp")

        self.assertIn("mkdir demo", preview)
        self.assertIn("High risk", preview)
        self.assertIn("/tmp", preview)

        destructive_preview = policy.format_preview(
            "rm -rf /", CommandPolicy.RISK_DESTRUCTIVE, "/home"
        )
        self.assertIn("Destructive", destructive_preview)

    def test_terminal_tool_includes_risk_and_directory_in_metadata(self):
        task = Task(tool="terminal", action="execute", target="mkdir demo")
        tool = TerminalTool(working_directory="/tmp")

        result = tool.execute(task)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "confirmation_required")
        self.assertEqual(result.metadata["risk_level"], CommandPolicy.RISK_HIGH)
        self.assertEqual(result.metadata["working_directory"], "/tmp")
        self.assertIn("High risk", result.message)
        self.assertIn("/tmp", result.message)

    # --- Sprint 12.3: Task History tests ---

    def test_task_history_records_and_retrieves_entries(self):
        history = TaskHistory()
        task1 = Task(tool="app", action="open", target="chrome")
        result1 = ActionResult(success=True, message="Opened")
        history.record(task1, result1)

        task2 = Task(tool="app", action="open", target="broken")
        result2 = ActionResult(success=False, message="Failed", error="unknown")
        history.record(task2, result2)

        entries = history.entries
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["task"], "app:open chrome")
        self.assertTrue(entries[0]["success"])
        self.assertEqual(entries[1]["task"], "app:open broken")
        self.assertFalse(entries[1]["success"])

    def test_task_history_respects_max_size(self):
        history = TaskHistory(max_size=2)
        
        for i in range(3):
            task = Task(tool="test", action="run", target=str(i))
            result = ActionResult(success=True, message=str(i))
            history.record(task, result)

        entries = history.entries
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["message"], "1")
        self.assertEqual(entries[1]["message"], "2")

    def test_executor_records_history_on_completion_and_failure(self):
        class HistoryToolManager:
            def execute(self, task):
                return ActionResult(success=(task.target == "success"), message=task.target)

        task_queue = TaskQueue()
        task_queue.enqueue(Task(tool="app", action="open", target="success"))
        task_queue.enqueue(Task(tool="app", action="open", target="failure"))
        history = TaskHistory()
        executor = Executor(task_queue, HistoryToolManager(), task_history=history)

        executor.execute_next()
        executor.execute_next()

        entries = history.entries
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[0]["success"])
        self.assertFalse(entries[1]["success"])

    # --- Sprint 13.0: Browser Skill tests ---

    def test_browser_tool_opens_a_url(self):
        class MockRunner:
            def __init__(self):
                self.calls = []
            def __call__(self, args, **kwargs):
                self.calls.append(args)

        runner = MockRunner()
        tool = BrowserTool(command_runner=runner)
        task = Task(tool="browser", action="open_url", target="https://example.com")
        
        result = tool.execute(task)
        
        self.assertTrue(result.success)
        self.assertEqual(runner.calls[0], ["open", "https://example.com"])

    def test_browser_tool_searches_the_web(self):
        class MockRunner:
            def __init__(self):
                self.calls = []
            def __call__(self, args, **kwargs):
                self.calls.append(args)

        runner = MockRunner()
        tool = BrowserTool(command_runner=runner)
        task = Task(tool="browser", action="search", target="test query")
        
        result = tool.execute(task)
        
        self.assertTrue(result.success)
        self.assertEqual(runner.calls[0], ["open", "https://www.google.com/search?q=test+query"])

    def test_browser_tool_rejects_invalid_url(self):
        tool = BrowserTool()
        task = Task(tool="browser", action="open_url", target="ftp://example.com")
        
        result = tool.execute(task)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "invalid_url")

    def test_planner_routes_url_to_browser_and_app_name_to_app(self):
        tasks = Planner().plan("open https://google.com")
        self.assertEqual(tasks[0].tool, "browser")
        self.assertEqual(tasks[0].action, "open_url")
        self.assertEqual(tasks[0].target, "https://google.com")

        tasks = Planner().plan("open chrome")
        self.assertEqual(tasks[0].tool, "app")
        self.assertEqual(tasks[0].action, "open")
        self.assertEqual(tasks[0].target, "chrome")

        tasks = Planner().plan("search python docs")
        self.assertEqual(tasks[0].tool, "browser")
        self.assertEqual(tasks[0].action, "search")
        self.assertEqual(tasks[0].target, "python docs")

    # --- Sprint 13.1: Context-Aware Planning tests ---

    def test_planner_resolves_this_using_context_manager(self):
        class MockContextManager:
            def get_active_context(self):
                return ActionResult(success=True, message="", data={"application": "Finder", "window_title": "ProjectX"})
        
        planner = Planner(context_manager=MockContextManager())
        tasks = planner.plan("open this in vscode")
        
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].tool, "terminal")
        self.assertEqual(tasks[0].action, "execute")
        self.assertEqual(tasks[0].target, 'open -a "vscode" "ProjectX"')

    def test_planner_creates_terminal_task_for_open_in_app(self):
        planner = Planner()
        tasks = planner.plan("open myfile.txt in TextEdit")
        
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].tool, "terminal")
        self.assertEqual(tasks[0].action, "execute")
        self.assertEqual(tasks[0].target, 'open -a "TextEdit" "myfile.txt"')

    def test_planner_leaves_this_alone_if_context_fails(self):
        class MockContextManager:
            def get_active_context(self):
                return ActionResult(success=False, message="Failed")
        
        planner = Planner(context_manager=MockContextManager())
        tasks = planner.plan("open this in vscode")
        
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].tool, "terminal")
        self.assertEqual(tasks[0].action, "execute")
        self.assertEqual(tasks[0].target, 'open -a "vscode" "this"')

    # --- Sprint 13.2: Memory Subsystem tests ---

    def test_memory_store_operations(self):
        from memory.memory_store import MemoryStore
        store = MemoryStore(storage_path="/tmp/test_memory_store.json")
        store.storage_path.unlink(missing_ok=True)
        store._facts.clear()
        
        store.set("Name", "Edith")
        self.assertEqual(store.get("name"), "Edith")
        self.assertTrue(store.delete("NAME"))
        self.assertFalse(store.delete("NAME"))

    def test_memory_store_persists_to_disk(self):
        from memory.memory_store import MemoryStore
        import json
        from pathlib import Path
        
        path = Path("/tmp/test_edith_memory_1.json")
        path.unlink(missing_ok=True)
        
        store = MemoryStore(storage_path=str(path))
        store.set("user", "Alice")
        
        self.assertTrue(path.exists())
        with open(path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["user"], "Alice")
        
    def test_memory_store_loads_from_disk_on_init(self):
        from memory.memory_store import MemoryStore
        import json
        from pathlib import Path
        
        path = Path("/tmp/test_edith_memory_2.json")
        path.unlink(missing_ok=True)
        with open(path, "w") as f:
            json.dump({"theme": "dark"}, f)
            
        store = MemoryStore(storage_path=str(path))
        self.assertEqual(store.get("theme"), "dark")

    def test_memory_tool_remembers_and_recalls(self):
        from tools.memory_tool import MemoryTool
        from memory.memory_store import MemoryStore
        store = MemoryStore(storage_path="/tmp/test_memory_tool.json")
        store.storage_path.unlink(missing_ok=True)
        store._facts.clear()
        tool = MemoryTool(memory_store=store)

        task_rem = Task("memory", "remember", "project", parameters={"value": "Antigravity"})
        res_rem = tool.execute(task_rem)
        self.assertTrue(res_rem.success)
        self.assertEqual(store.get("project"), "Antigravity")

        task_rec = Task("memory", "recall", "project")
        res_rec = tool.execute(task_rec)
        self.assertTrue(res_rec.success)
        self.assertEqual(res_rec.data["value"], "Antigravity")

        task_forget = Task("memory", "forget", "project")
        res_forget = tool.execute(task_forget)
        self.assertTrue(res_forget.success)
        self.assertIsNone(store.get("project"))

    def test_planner_creates_memory_tasks(self):
        planner = Planner()
        
        t1 = planner.plan("remember user is Bob")
        self.assertEqual(t1[0].tool, "memory")
        self.assertEqual(t1[0].action, "remember")
        self.assertEqual(t1[0].target, "user")
        self.assertEqual(t1[0].parameters["value"], "Bob")

        t2 = planner.plan("recall user")
        self.assertEqual(t2[0].tool, "memory")
        self.assertEqual(t2[0].action, "recall")
        self.assertEqual(t2[0].target, "user")

        t3 = planner.plan("forget user")
        self.assertEqual(t3[0].tool, "memory")
        self.assertEqual(t3[0].action, "forget")
        self.assertEqual(t3[0].target, "user")

    # --- Sprint 14.1: Perception Subsystem tests ---
    
    def test_planner_creates_perception_task(self):
        planner = Planner()
        t1 = planner.plan("take screenshot")
        self.assertEqual(t1[0].tool, "perception")
        self.assertEqual(t1[0].action, "capture_screen")
        
        t2 = planner.plan("capture screen")
        self.assertEqual(t2[0].tool, "perception")
        self.assertEqual(t2[0].action, "capture_screen")

    def test_perception_tool_returns_action_result_without_executing_in_tests(self):
        # We test failure path to avoid actually running screencapture in CI/tests
        from tools.perception_tool import PerceptionTool
        tool = PerceptionTool(save_dir="/System/Library/FakeDirToFail")
        # Ensure it handles bad actions
        res_bad = tool.execute(Task("perception", "invalid"))
        self.assertFalse(res_bad.success)
        self.assertEqual(res_bad.error, "unsupported_action")
        
        # Test exception path (trying to mkdir in /System usually fails on mac)
        res_err = tool.execute(Task("perception", "capture_screen"))
        # If it doesn't fail, it returns True, but we just want to ensure it returns ActionResult
        self.assertTrue(hasattr(res_err, 'success'))

    def test_planner_creates_analyze_screen_task(self):
        """Planner should route screen-analysis phrases to perception:analyze_screen."""
        planner = Planner()

        for phrase in [
            "analyze screen",
            "what's on my screen",
            "what is on my screen",
            "read my screen",
            "inspect screen",
            "explain the error on my screen",
        ]:
            tasks = planner.plan(phrase)
            self.assertEqual(len(tasks), 1, msg=f"Phrase '{phrase}' should produce one task")
            self.assertEqual(tasks[0].tool, "perception", msg=f"Expected perception tool for '{phrase}'")
            self.assertEqual(tasks[0].action, "analyze_screen", msg=f"Expected analyze_screen action for '{phrase}'")

    def test_perception_tool_analyze_screen_with_mocked_llm(self):
        """PerceptionTool.analyze_screen should return vision analysis from the LLM."""
        from tools.perception_tool import PerceptionTool
        from unittest.mock import MagicMock, patch
        import tempfile
        from pathlib import Path

        mock_llm = MagicMock()
        mock_llm.ask_vision.return_value = "There is a code editor open with Python code."

        tool = PerceptionTool(llm=mock_llm)

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "vision"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Write a minimal dummy PNG so base64 encoding succeeds
            dummy = cache_dir / "vision_test_dummy.png"
            dummy.write_bytes(b"\x89PNG\r\n\x1a\n")

            with patch("tools.perception_tool._CACHE_DIR", cache_dir):
                with patch("subprocess.run", return_value=None):
                    result = tool._analyze("What is on my screen?")

        self.assertTrue(result.success)
        self.assertIn("code editor", result.message)
        self.assertEqual(result.data["analysis"], "There is a code editor open with Python code.")

    def test_llm_ask_vision_returns_error_on_missing_file(self):
        """LLM.ask_vision should return an error string (not raise) when image is missing."""
        from core.llm import LLM
        llm = LLM()
        result = llm.ask_vision("What is on screen?", "/nonexistent/path/screen.png")
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("Vision Error:"))

    # --- Sprint 14.2: File Reading Capability tests ---

    def test_file_tool_reads_file_contents(self):
        from tools.file_tool import FileTool
        from pathlib import Path
        
        path = Path("/tmp/test_edith_read.txt")
        path.write_text("Line 1\nLine 2")
        
        tool = FileTool()
        result = tool.execute(Task("file", "read", str(path)))
        
        self.assertTrue(result.success)
        self.assertIn("Line 1", result.message)
        self.assertIn("Line 2", result.data["content"])
        
    def test_file_tool_read_handles_missing_files(self):
        from tools.file_tool import FileTool
        
        tool = FileTool()
        result = tool.execute(Task("file", "read", "/tmp/does_not_exist_12345.txt"))
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "path_not_found")
        
    def test_planner_creates_read_file_task(self):
        planner = Planner()
        
        t1 = planner.plan("read file /tmp/hello.txt")
        self.assertEqual(t1[0].tool, "file")
        self.assertEqual(t1[0].action, "read")
        self.assertEqual(t1[0].target, "/tmp/hello.txt")
        
    # --- Sprint 14.3: Multi-Target File Operations tests ---
    
    def test_planner_creates_multiple_tasks_for_multi_target_delete(self):
        planner = Planner()
        tasks = planner.plan("delete file A.txt, B.txt and C.txt")
        
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].target, "A.txt")
        self.assertEqual(tasks[1].target, "B.txt")
        self.assertEqual(tasks[2].target, "C.txt")
        self.assertTrue(all(t.action == "delete" and t.tool == "file" for t in tasks))

    def test_planner_creates_multiple_tasks_for_multi_target_create(self):
        planner = Planner()
        tasks = planner.plan("create folder X and Y")
        
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].target, "X")
        self.assertEqual(tasks[1].target, "Y")
        self.assertTrue(all(t.action == "create_folder" and t.tool == "file" for t in tasks))

    # --- Sprint 15.0: System Auditing tests ---
    
    def test_audit_logger_records_task_outcome(self):
        from security.audit_logger import AuditLogger
        from pathlib import Path
        import json
        
        log_path = Path("/tmp/test_edith_audit.log")
        log_path.unlink(missing_ok=True)
        
        logger = AuditLogger(log_path=str(log_path))
        task = Task("terminal", "execute", "echo hello")
        res = ActionResult(True, "hello", execution_time=1.5, metadata={"risk_level": "none"})
        
        logger.log_task(task, res)
        
        self.assertTrue(log_path.exists())
        with open(log_path, "r") as f:
            lines = f.readlines()
            
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["tool"], "terminal")
        self.assertEqual(entry["action"], "execute")
        self.assertEqual(entry["target"], "echo hello")
        self.assertTrue(entry["success"])
        self.assertEqual(entry["metadata"]["risk_level"], "none")
        self.assertEqual(entry["execution_time_ms"], 1500.0)

    def test_executor_uses_audit_logger(self):
        from security.audit_logger import AuditLogger
        from pathlib import Path
        
        log_path = Path("/tmp/test_edith_executor_audit.log")
        log_path.unlink(missing_ok=True)
        
        logger = AuditLogger(log_path=str(log_path))
        queue = TaskQueue()
        queue.enqueue(Task("calculator", "evaluate", "2+2"))
        executor = Executor(queue, tool_manager=ToolManager(), audit_logger=logger)
        
        executor.execute_all()
        
        self.assertTrue(log_path.exists())
        with open(log_path, "r") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)

    # --- Sprint 15.1: Clipboard Awareness tests ---
    
    def test_context_manager_reads_clipboard(self):
        from context.context_manager import ContextManager
        import subprocess
        
        # Test requires actual pbcopy/pbpaste on mac, if we can't we mock or just check it returns action result
        ctx = ContextManager()
        res = ctx.get_clipboard()
        self.assertTrue(hasattr(res, "success"))


    def test_planner_substitutes_clipboard(self):
        from context.context_manager import ContextManager
        
        class FakeContextManager:
            def get_active_context(self):
                return ActionResult(False, "fail")
            def get_clipboard(self):
                return ActionResult(True, "success", data={"clipboard": "CopiedData123"})
                
        planner = Planner(context_manager=FakeContextManager())
        tasks = planner.plan("remember temp is clipboard")
        self.assertEqual(tasks[0].tool, "memory")
        self.assertEqual(tasks[0].target, "temp")
        self.assertEqual(tasks[0].parameters["value"], "CopiedData123")

    # --- Sprint 16.0: AI Planner tests ---

    def _make_ai_planner(self):
        """Helper to create an AIPlanner with real capabilities."""
        from brain.ai_planner import AIPlanner
        caps = {
            cap["name"]: cap
            for cap in ToolManager().get_capabilities()
        }
        return AIPlanner(capabilities=caps)

    def test_ai_planner_extracts_valid_json_tasks(self):
        from brain.ai_planner import AIPlanner
        planner = self._make_ai_planner()

        raw = '[{"tool":"file","action":"create_folder","target":"projects"},{"tool":"file","action":"create_file","target":"projects/README.md"}]'
        parsed = planner._extract_json(raw)
        tasks = planner._validate_tasks(parsed)

        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].tool, "file")
        self.assertEqual(tasks[0].action, "create_folder")
        self.assertEqual(tasks[0].target, "projects")
        self.assertEqual(tasks[1].action, "create_file")

    def test_ai_planner_handles_markdown_code_fences(self):
        planner = self._make_ai_planner()

        raw = '```json\n[{"tool":"app","action":"open","target":"chrome"}]\n```'
        parsed = planner._extract_json(raw)
        tasks = planner._validate_tasks(parsed)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].tool, "app")
        self.assertEqual(tasks[0].target, "chrome")

    def test_ai_planner_returns_empty_for_malformed_json(self):
        planner = self._make_ai_planner()

        raw = 'Sure! Here is what I would do: {broken json...'
        parsed = planner._extract_json(raw)
        self.assertEqual(parsed, [])

    def test_ai_planner_filters_hallucinated_tools(self):
        planner = self._make_ai_planner()

        raw = '[{"tool":"email","action":"send","target":"hello@test.com"},{"tool":"app","action":"open","target":"safari"}]'
        parsed = planner._extract_json(raw)
        tasks = planner._validate_tasks(parsed)

        # "email" tool doesn't exist — should be filtered out
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].tool, "app")

    def test_ai_planner_filters_invalid_actions(self):
        planner = self._make_ai_planner()

        raw = '[{"tool":"file","action":"encrypt","target":"secret.txt"}]'
        parsed = planner._extract_json(raw)
        tasks = planner._validate_tasks(parsed)

        # "encrypt" is not a valid file action
        self.assertEqual(len(tasks), 0)

    def test_ai_planner_returns_empty_for_conversation(self):
        planner = self._make_ai_planner()

        raw = '[]'
        parsed = planner._extract_json(raw)
        tasks = planner._validate_tasks(parsed)

        self.assertEqual(len(tasks), 0)

    def test_ai_planner_handles_ollama_failure_gracefully(self):
        """If Ollama is unreachable, plan() returns [] — no crash."""
        from brain.ai_planner import AIPlanner
        planner = AIPlanner(capabilities={})
        # This calls real Ollama which may or may not be running — 
        # but AIPlanner.plan() wraps everything in try/except
        result = planner.plan("this should not crash")
        self.assertIsInstance(result, list)

    # ------------------------------------------------------------------
    # Sprint 18 — Voice Output & Smart Output Router
    # ------------------------------------------------------------------

    def test_output_router_classifies_code_as_display(self):
        """Response containing code blocks should be classified as code."""
        from voice.output_router import OutputRouter
        response = "Here is the code:\n```python\nprint('hello')\n```"
        self.assertEqual(OutputRouter.classify(response), "code")

    def test_output_router_classifies_table_as_display(self):
        """Response containing markdown tables should be classified as table."""
        from voice.output_router import OutputRouter
        response = "| Name | Age |\n|------|-----|\n| Tony | 30 |"
        self.assertEqual(OutputRouter.classify(response), "table")

    def test_output_router_classifies_short_text_as_speak(self):
        """Short conversational responses should be classified as speak."""
        from voice.output_router import OutputRouter
        response = "The current time is 3:45 PM."
        self.assertEqual(OutputRouter.classify(response), "speak")

    def test_output_router_classifies_long_text_as_display(self):
        """Responses over 500 characters should be classified as display."""
        from voice.output_router import OutputRouter
        response = "A " * 300  # 600 characters
        self.assertEqual(OutputRouter.classify(response), "display")

    def test_output_router_classifies_empty_as_speak(self):
        """Empty responses should default to speak."""
        from voice.output_router import OutputRouter
        self.assertEqual(OutputRouter.classify(""), "speak")
        self.assertEqual(OutputRouter.classify(None), "speak")

    # --- Sprint 21.1: Adaptive Output Renderer card tests ---

    def test_output_router_render_card_format(self):
        """render_card should produce a well-formed Unicode box with title and rows."""
        from voice.output_router import OutputRouter
        rows = [("Charge", "74%"), ("Status", "Discharging"), ("Source", "Battery Power")]
        card = OutputRouter.render_card("Battery Status", rows, icon="🔋")

        self.assertIn("Battery Status", card)
        self.assertIn("Charge", card)
        self.assertIn("74%", card)
        self.assertIn("Discharging", card)
        # Check box-drawing characters are present
        self.assertIn("╭", card)
        self.assertIn("╰", card)
        self.assertIn("│", card)
        self.assertIn("┬", card)

    def test_output_router_card_spoken_summary(self):
        """card_spoken_summary should return a natural sentence from key rows."""
        from voice.output_router import OutputRouter
        rows = [("Charge", "74%"), ("Status", "Discharging"), ("Source", "Battery Power")]
        summary = OutputRouter.card_spoken_summary("Battery Status", rows)

        self.assertIn("Battery Status", summary)
        self.assertIn("74%", summary)
        self.assertIn("Discharging", summary)
        self.assertTrue(summary.endswith("."))

    def test_output_router_extract_card_data_for_battery(self):
        """extract_card_data should map battery_status ActionResult to card rows."""
        from voice.output_router import OutputRouter
        from brain.action_result import ActionResult

        result = ActionResult(
            success=True,
            message="Battery is at 74%.",
            data={"percentage": 74, "state": "discharging", "source": "Battery Power", "time_remaining": None},
            metadata={"action": "battery_status"},
        )

        card_data = OutputRouter.extract_card_data(result)
        self.assertIsNotNone(card_data)
        title, icon, rows = card_data
        self.assertEqual(title, "Battery Status")
        self.assertEqual(icon, "🔋")
        # Rows should contain Charge and Status at minimum
        labels = [r[0] for r in rows]
        self.assertIn("Charge", labels)
        self.assertIn("Status", labels)

    def test_output_router_extract_card_data_returns_none_for_plain_text(self):
        """extract_card_data should return None for results without structured data."""
        from voice.output_router import OutputRouter
        from brain.action_result import ActionResult

        result = ActionResult(
            success=True,
            message="All done.",
            data={},
            metadata={"action": "create_file"},
        )
        self.assertIsNone(OutputRouter.extract_card_data(result))
        self.assertIsNone(OutputRouter.extract_card_data(None))

    # --- Sprint 21.1: Situational Renderers ---

    def test_situation_detector_default_mode(self):
        """SituationDetector should start in default mode."""
        from context.situation_detector import SituationDetector
        sd = SituationDetector()
        self.assertEqual(sd.mode, "default")

    def test_situation_detector_set_valid_mode(self):
        """SituationDetector.set_mode should accept known modes."""
        from context.situation_detector import SituationDetector
        sd = SituationDetector()
        self.assertTrue(sd.set_mode("driving"))
        self.assertEqual(sd.mode, "driving")
        self.assertTrue(sd.set_mode("meeting"))
        self.assertEqual(sd.mode, "meeting")

    def test_situation_detector_rejects_unknown_mode(self):
        """SituationDetector.set_mode should return False for unknown modes."""
        from context.situation_detector import SituationDetector
        sd = SituationDetector()
        self.assertFalse(sd.set_mode("flying"))
        self.assertEqual(sd.mode, "default")  # unchanged

    def test_render_for_mode_driving_no_screen(self):
        """Driving mode should produce voice output and no screen card."""
        from voice.output_router import OutputRouter, RenderOutput
        from brain.action_result import ActionResult

        result = ActionResult(
            success=True,
            message="Battery is at 74%.",
            data={"percentage": 74, "state": "discharging", "source": "Battery Power"},
            metadata={"action": "battery_status"},
        )
        render = OutputRouter.render_for_mode("driving", action_result=result)

        self.assertIsInstance(render, RenderOutput)
        self.assertIsNone(render.screen)          # no rich card in driving mode
        self.assertIsNotNone(render.voice)        # crisp spoken summary
        self.assertIsNotNone(render.follow_up)    # e.g. "Want me to navigate?"
        self.assertEqual(render.mode, "driving")
        self.assertIn("74%", render.voice)

    def test_render_for_mode_meeting_silent(self):
        """Meeting mode should produce screen text only — voice is suppressed."""
        from voice.output_router import OutputRouter, RenderOutput
        from brain.action_result import ActionResult

        result = ActionResult(
            success=True,
            message="Battery is at 74%.",
            data={"percentage": 74, "state": "discharging", "source": "Battery Power"},
            metadata={"action": "battery_status"},
        )
        render = OutputRouter.render_for_mode("meeting", action_result=result)

        self.assertIsInstance(render, RenderOutput)
        self.assertIsNotNone(render.screen)       # compact notification line
        self.assertIsNone(render.voice)           # silent in meeting
        self.assertIsNone(render.follow_up)
        self.assertEqual(render.mode, "meeting")
        self.assertTrue(render.screen.startswith("📌"))

    def test_render_for_mode_desk_full_card(self):
        """Desk mode should produce the full card on screen with an action hint."""
        from voice.output_router import OutputRouter, RenderOutput
        from brain.action_result import ActionResult

        result = ActionResult(
            success=True,
            message="Volume is at 65%.",
            data={"volume": 65, "muted": False},
            metadata={"action": "volume_get"},
        )
        render = OutputRouter.render_for_mode("desk", action_result=result)

        self.assertIsInstance(render, RenderOutput)
        self.assertIsNotNone(render.screen)       # rich card + action hint
        self.assertIsNotNone(render.voice)        # spoken executive summary
        self.assertEqual(render.mode, "desk")
        self.assertIn("╭", render.screen)         # Unicode box present
        self.assertIn("↳", render.screen)         # action hint present
        self.assertIn("65%", render.voice)

    def test_output_router_spoken_notice_for_code(self):
        from voice.output_router import OutputRouter
        response = "```python\nprint('hello')\n```"
        notice = OutputRouter.get_spoken_notice(response)
        self.assertIn("code", notice.lower())
        self.assertIn("python", notice.lower())

    def test_output_router_spoken_notice_for_table(self):
        """Table responses should produce a spoken notice mentioning table."""
        from voice.output_router import OutputRouter
        response = "| Name | Age |\n|------|-----|\n| Tony | 30 |"
        notice = OutputRouter.get_spoken_notice(response)
        self.assertIn("table", notice.lower())

    def test_voice_engine_sanitize_strips_code_fences(self):
        """VoiceEngine._sanitize should remove code blocks from text."""
        from voice.voice_engine import VoiceEngine
        text = "Here is code:\n```python\nprint('hi')\n```\nDone."
        result = VoiceEngine._sanitize(text)
        self.assertNotIn("```", result)
        self.assertNotIn("print", result)
        self.assertIn("Done", result)

    def test_voice_engine_sanitize_strips_markdown(self):
        """VoiceEngine._sanitize should remove markdown formatting."""
        from voice.voice_engine import VoiceEngine
        text = "**Bold text** and `inline code` and *italic*"
        result = VoiceEngine._sanitize(text)
        self.assertNotIn("**", result)
        self.assertNotIn("`", result)
        self.assertNotIn("*", result)
        self.assertIn("Bold text", result)
        self.assertIn("inline code", result)

    def test_voice_engine_speak_with_mocked_subprocess(self):
        """VoiceEngine.speak should invoke the macOS say command."""
        from voice.voice_engine import VoiceEngine
        from unittest.mock import patch, MagicMock
        engine = VoiceEngine()
        with patch("voice.voice_engine.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            engine.speak("Hello world")
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertEqual(args[0], "say")
            self.assertIn("-v", args)
            self.assertIn("Tara", args)

    # ------------------------------------------------------------------
    # Sprint 18.1 — JARVIS Voice Upgrade & Dual-Channel Output
    # ------------------------------------------------------------------

    def test_voice_engine_speak_supports_rate_override(self):
        """VoiceEngine.speak should allow overriding the rate parameter."""
        from voice.voice_engine import VoiceEngine
        from unittest.mock import patch, MagicMock
        engine = VoiceEngine()
        with patch("voice.voice_engine.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            engine.speak("Warning", rate=160)
            args = mock_popen.call_args[0][0]
            self.assertIn("-r", args)
            self.assertIn("160", args)

    def test_voice_personality_greeting_time_aware(self):
        """VoicePersonality.get_greeting should reflect morning, afternoon, and evening."""
        import datetime
        from voice.voice_personality import VoicePersonality
        personality = VoicePersonality()

        morning = datetime.datetime(2026, 9, 10, 9, 0)
        afternoon = datetime.datetime(2026, 9, 10, 14, 0)
        evening = datetime.datetime(2026, 9, 10, 19, 0)

        self.assertIn("Good morning", personality.get_greeting(custom_time=morning))
        self.assertIn("Good afternoon", personality.get_greeting(custom_time=afternoon))
        self.assertIn("Good evening", personality.get_greeting(custom_time=evening))

    def test_voice_personality_greeting_uses_memory_name(self):
        """VoicePersonality should address user by name if stored in MemoryStore."""
        import datetime
        from voice.voice_personality import VoicePersonality
        from memory.memory_store import MemoryStore
        
        mem = MemoryStore(storage_path="/tmp/test_edith_voice_mem.json")
        mem.set("my name", "Satya")
        personality = VoicePersonality(memory_store=mem)

        evening = datetime.datetime(2026, 9, 10, 20, 0)
        greeting = personality.get_greeting(custom_time=evening)
        self.assertIn("Satya", greeting)
        self.assertIn("Good evening", greeting)

    def test_voice_personality_acknowledgment_rotates(self):
        """VoicePersonality.get_acknowledgment should return varied snappy phrases."""
        from voice.voice_personality import VoicePersonality
        personality = VoicePersonality()
        first = personality.get_acknowledgment()
        second = personality.get_acknowledgment()
        self.assertIsInstance(first, str)
        self.assertIsInstance(second, str)
        self.assertNotEqual(first, second)

    def test_voice_personality_confirmation_notice(self):
        """VoicePersonality should generate a clear authorization notice."""
        from voice.voice_personality import VoicePersonality
        personality = VoicePersonality()
        notice = personality.get_confirmation_notice(risk_level="high")
        self.assertIn("authorization", notice.lower())

    def test_output_router_extract_executive_summary_from_code(self):
        """OutputRouter should extract lead explanation before code block."""
        from voice.output_router import OutputRouter
        text = "Here is an iterative Fibonacci function. It runs in linear time.\n```python\ndef fib(n):\n    pass\n```"
        summary = OutputRouter.extract_executive_summary(text)
        self.assertIn("iterative Fibonacci function", summary)

    def test_output_router_dual_channel_spoken_notice(self):
        """OutputRouter.get_spoken_notice should combine executive summary with screen cue."""
        from voice.output_router import OutputRouter
        text = "Here is the Fibonacci calculation.\n```python\ndef fib(n):\n    pass\n```"
        notice = OutputRouter.get_spoken_notice(text)
        self.assertIn("Fibonacci calculation", notice)
        self.assertIn("screen", notice.lower())

    def test_planner_creates_name_recall_tasks(self):
        """Planner should recognize 'what is my name' and 'who am i'."""
        planner = Planner()
        for phrase in ["what is my name", "what is my name?", "what's my name", "who am i", "who am i?"]:
            tasks = planner.plan(phrase)
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].tool, "memory")
            self.assertEqual(tasks[0].action, "recall")
            self.assertEqual(tasks[0].target, "my name")

    def test_memory_tool_name_personalization(self):
        """MemoryTool should say 'Your name is X' instead of 'my name is X'."""
        from tools.memory_tool import MemoryTool
        from memory.memory_store import MemoryStore
        store = MemoryStore(storage_path="/tmp/test_mem_personal.json")
        store.storage_path.unlink(missing_ok=True)
        store._facts.clear()
        tool = MemoryTool(memory_store=store)

        rem_task = Task("memory", "remember", "my name", parameters={"value": "Satya"})
        res_rem = tool.execute(rem_task)
        self.assertIn("your name is satya", res_rem.message.lower())

        rec_task = Task("memory", "recall", "my name")
        res_rec = tool.execute(rec_task)
        self.assertEqual(res_rec.message, "Your name is Satya.")

    def test_voice_engine_human_speech_rate(self):
        """VoiceEngine should default to standard speech rate (190 WPM)."""
        from voice.voice_engine import VoiceEngine
        engine = VoiceEngine()
        self.assertEqual(engine.DEFAULT_RATE, 190)

    def test_build_chat_messages_injects_guidelines_and_name(self):
        """_build_chat_messages should inject explanation rules and user name into system prompt."""
        from app import _build_chat_messages
        from memory.memory_store import MemoryStore
        from core.chat import ChatSession

        mem = MemoryStore(storage_path="/tmp/test_chat_msg.json")
        mem.set("my name", "Satya")
        chat = ChatSession()
        chat.clear()
        chat.add_user("how to sort a list?")

        messages = _build_chat_messages(chat, memory_store=mem)
        self.assertTrue(len(messages) >= 2)
        system_msg = messages[0]["content"]
        self.assertIn("Satya", system_msg)
        self.assertIn("multiple or large steps", system_msg)
        self.assertIn("interactive check", system_msg)
        self.assertIn("Dynamic Tone", system_msg)

    def test_output_router_format_spoken_sentence(self):
        """OutputRouter.format_spoken_sentence should frame raw numbers, dates, and times into natural sentences."""
        from voice.output_router import OutputRouter

        # Raw number / math results
        self.assertEqual(OutputRouter.format_spoken_sentence("4"), "The result is 4.")
        self.assertEqual(OutputRouter.format_spoken_sentence("42"), "The result is 42.")
        self.assertEqual(OutputRouter.format_spoken_sentence("100.5"), "The result is 100.5.")

        # Time
        self.assertEqual(OutputRouter.format_spoken_sentence("08:33:17 PM"), "The current time is 08:33:17 PM.")
        self.assertEqual(OutputRouter.format_spoken_sentence("3:45 PM"), "The current time is 3:45 PM.")

        # Date
        self.assertEqual(OutputRouter.format_spoken_sentence("10 September 2026"), "Today's date is 10 September 2026.")
        self.assertEqual(OutputRouter.format_spoken_sentence("September 10, 2026"), "Today's date is September 10, 2026.")
        self.assertEqual(OutputRouter.format_spoken_sentence("2026-09-10"), "Today's date is 2026-09-10.")

        # Pure single word (spoken directly)
        self.assertEqual(OutputRouter.format_spoken_sentence("Yes"), "Yes")
        self.assertEqual(OutputRouter.format_spoken_sentence("Done"), "Done")
        self.assertEqual(OutputRouter.format_spoken_sentence("Confirmed"), "Confirmed")

        # Full sentence preserved
        self.assertEqual(OutputRouter.format_spoken_sentence("All systems green."), "All systems green.")
        self.assertEqual(OutputRouter.format_spoken_sentence(""), "")

    def test_output_router_theory_explanation_detection(self):
        """OutputRouter.is_theory_or_explanation should identify theory questions and structured explanations."""
        from voice.output_router import OutputRouter

        # Query triggers
        self.assertTrue(OutputRouter.is_theory_or_explanation("Binary search is ...", "explain how a binary search function works in python"))
        self.assertTrue(OutputRouter.is_theory_or_explanation("Here is how it works", "how does quicksort work?"))
        self.assertTrue(OutputRouter.is_theory_or_explanation("Details...", "what is dynamic programming?"))

        # Structured response markers
        structured_reply = (
            "### Purpose\nFast search.\n"
            "### Key Components\nLow and high pointers.\n"
            "### Input\nSorted array.\n"
            "### Output\nIndex or -1.\n"
            "### Common Errors\nUnsorted input."
        )
        self.assertTrue(OutputRouter.is_theory_or_explanation(structured_reply, "binary search"))

        # Non-theory request
        self.assertFalse(OutputRouter.is_theory_or_explanation("```python\nx = 1\n```", "give me python code for fibonacci"))

    def test_output_router_format_spoken_explanation(self):
        """OutputRouter.format_spoken_explanation should preserve descriptive sections and bridge code blocks."""
        from voice.output_router import OutputRouter

        sample_explanation = (
            "### 1. Purpose\nBinary search locates items in O(log n) time.\n\n"
            "### 2. Key Components\nUses low, mid, and high pointers.\n\n"
            "### 3. Input\nA sorted list and a target item.\n\n"
            "### 4. Output\nThe index of the item or -1.\n\n"
            "### 5. Common Errors & Pitfalls\nPassing an unsorted array or infinite loop on mid.\n\n"
            "### 6. Example\n"
            "```python\ndef binary_search(arr, target):\n    return 0\n```\n"
            "For example, searching for 7 in [1, 3, 5, 7, 9] yields index 3.\n\n"
            "### 7. Interactive Check\nDid this explanation make sense, Boss?"
        )

        spoken = OutputRouter.format_spoken_explanation(sample_explanation)
        self.assertIn("Purpose", spoken)
        self.assertIn("Key Components", spoken)
        self.assertIn("Input", spoken)
        self.assertIn("Output", spoken)
        self.assertIn("Common Errors & Pitfalls", spoken)
        self.assertIn("I've placed the python code implementation on your screen.", spoken)
        self.assertIn("Did this explanation make sense, Boss?", spoken)
        self.assertNotIn("def binary_search", spoken)

    def test_system_tool_metadata_and_registration(self):
        """SystemTool should be properly registered in ToolManager with required metadata."""
        from tools.system_tool import SystemTool
        tool = SystemTool()
        meta = tool.metadata()
        self.assertEqual(meta["name"], "system")
        self.assertIn("volume_set", meta["supported_actions"])
        self.assertIn("battery_status", meta["supported_actions"])
        self.assertIn("dark_mode_set", meta["supported_actions"])
        self.assertIn("lock_screen", meta["supported_actions"])

        manager = ToolManager()
        self.assertIn("system", manager.tools_by_name)
        self.assertIsInstance(manager.tools_by_name["system"], SystemTool)

    def test_planner_creates_system_tasks(self):
        """Planner should recognize system hardware and settings commands."""
        planner = Planner()

        # Volume
        tasks = planner.plan("set volume to 40%")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].tool, "system")
        self.assertEqual(tasks[0].action, "volume_set")
        self.assertEqual(tasks[0].parameters["level"], 40)

        tasks = planner.plan("volume 75")
        self.assertEqual(tasks[0].parameters["level"], 75)

        tasks = planner.plan("volume up")
        self.assertEqual(tasks[0].action, "volume_set")
        self.assertEqual(tasks[0].parameters["relative"], 10)

        tasks = planner.plan("volume down")
        self.assertEqual(tasks[0].action, "volume_set")
        self.assertEqual(tasks[0].parameters["relative"], -10)

        tasks = planner.plan("mute")
        self.assertEqual(tasks[0].action, "volume_mute")

        tasks = planner.plan("unmute")
        self.assertEqual(tasks[0].action, "volume_unmute")

        tasks = planner.plan("what is the volume")
        self.assertEqual(tasks[0].action, "volume_get")

        # Battery
        for phrase in ["battery", "check battery", "battery status", "what is my battery"]:
            tasks = planner.plan(phrase)
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].tool, "system")
            self.assertEqual(tasks[0].action, "battery_status")

        # Dark Mode
        tasks = planner.plan("turn on dark mode")
        self.assertEqual(tasks[0].action, "dark_mode_set")
        self.assertTrue(tasks[0].parameters["enabled"])

        tasks = planner.plan("turn off dark mode")
        self.assertEqual(tasks[0].action, "dark_mode_set")
        self.assertFalse(tasks[0].parameters["enabled"])

        tasks = planner.plan("toggle dark mode")
        self.assertEqual(tasks[0].action, "dark_mode_toggle")

        tasks = planner.plan("is dark mode on")
        self.assertEqual(tasks[0].action, "dark_mode_get")

        # Lock Screen
        tasks = planner.plan("lock screen")
        self.assertEqual(tasks[0].action, "lock_screen")

    @patch("subprocess.run")
    def test_system_tool_battery_parsing(self, mock_run):
        """SystemTool should parse pmset output into structured battery info."""
        from tools.system_tool import SystemTool
        tool = SystemTool()

        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="Now drawing from 'Battery Power'\n -InternalBattery-0 (id=123)\t85%; discharging; 3:45 remaining present: true\n",
            stderr="",
        )

        task = Task("system", "battery_status")
        result = tool.execute(task)

        self.assertTrue(result.success)
        self.assertIn("85%", result.message)
        self.assertIn("discharging", result.message)
        self.assertEqual(result.data["percentage"], 85)
        self.assertEqual(result.data["state"], "discharging")
        self.assertEqual(result.data["source"], "Battery Power")
        self.assertEqual(result.data["time_remaining"], "3:45")

    @patch("subprocess.run")
    def test_system_tool_volume_execution(self, mock_run):
        """SystemTool should execute volume commands with clamped levels."""
        from tools.system_tool import SystemTool
        tool = SystemTool()

        # Set volume
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        task = Task("system", "volume_set", parameters={"level": 60})
        result = tool.execute(task)
        self.assertTrue(result.success)
        self.assertEqual(result.data["volume"], 60)
        self.assertIn("60%", result.message)

        # Set volume clamped
        task_clamped = Task("system", "volume_set", parameters={"level": 150})
        result_clamped = tool.execute(task_clamped)
        self.assertEqual(result_clamped.data["volume"], 100)

        # Mute / unmute
        task_mute = Task("system", "volume_mute")
        result_mute = tool.execute(task_mute)
        self.assertTrue(result_mute.success)
        self.assertTrue(result_mute.data["muted"])

        task_unmute = Task("system", "volume_unmute")
        result_unmute = tool.execute(task_unmute)
        self.assertTrue(result_unmute.success)
        self.assertFalse(result_unmute.data["muted"])

    def test_notification_tool_metadata_and_registration(self):
        """NotificationTool should declare metadata and be registered in ToolManager."""
        from tools.notification_tool import NotificationTool
        tool = NotificationTool()
        meta = tool.metadata()
        self.assertEqual(meta["name"], "notification")
        self.assertEqual(meta["resource_profile"], "on_demand")
        self.assertIn("notify", meta["supported_actions"])
        self.assertIn("set_timer", meta["supported_actions"])
        self.assertIn("list_timers", meta["supported_actions"])
        self.assertIn("cancel_timer", meta["supported_actions"])

        manager = ToolManager()
        self.assertIn("notification", manager.tools_by_name)
        self.assertIsInstance(manager.tools_by_name["notification"], NotificationTool)

    @patch("subprocess.run")
    def test_notification_tool_immediate_notify(self, mock_run):
        """NotificationTool should dispatch native macOS notification banners."""
        from tools.notification_tool import NotificationTool
        tool = NotificationTool()

        mock_run.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        task = Task("notification", "notify", parameters={"message": "Meeting in 5 mins", "title": "Work"})
        result = tool.execute(task)

        self.assertTrue(result.success)
        self.assertIn("Meeting in 5 mins", result.message)
        self.assertEqual(result.data["title"], "Work")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "osascript")
        self.assertIn("Meeting in 5 mins", args[2])

    def test_notification_tool_timer_lifecycle(self):
        """NotificationTool should schedule, list, and cancel active timers."""
        from tools.notification_tool import NotificationTool
        tool = NotificationTool()

        # Set timer
        task = Task("notification", "set_timer", parameters={"seconds": 60, "message": "Check oven"})
        result = tool.execute(task)
        self.assertTrue(result.success)
        self.assertIn("Check oven", result.message)
        timer_id = result.data["timer_id"]
        self.assertIsNotNone(timer_id)

        # List timers
        list_task = Task("notification", "list_timers")
        list_res = tool.execute(list_task)
        self.assertTrue(list_res.success)
        self.assertIn("Check oven", list_res.message)
        self.assertEqual(len(list_res.data["timers"]), 1)

        # Cancel timer
        cancel_task = Task("notification", "cancel_timer", parameters={"timer_id": timer_id})
        cancel_res = tool.execute(cancel_task)
        self.assertTrue(cancel_res.success)
        self.assertIn(f"Cancelled Timer #{timer_id}", cancel_res.message)

        # Listing again shows empty
        empty_res = tool.execute(list_task)
        self.assertEqual(empty_res.message, "No active timers.")

    @patch("subprocess.run")
    def test_notification_tool_timer_fire_with_voice(self, mock_run):
        """Timer callback should send banner and invoke voice_engine when set."""
        from tools.notification_tool import NotificationTool
        from unittest.mock import MagicMock

        mock_voice = MagicMock()
        tool = NotificationTool(voice_engine=mock_voice)

        tool._on_timer_fire(timer_id=99, title="EDITH", message="Stand up and stretch")

        mock_run.assert_called_once()
        mock_voice.speak.assert_called_once_with("Boss, reminder: Stand up and stretch")

    def test_planner_creates_notification_and_timer_tasks(self):
        """Planner should recognize reminder, timer, and notification commands."""
        planner = Planner()

        # Remind me in ...
        tasks = planner.plan("remind me in 15 minutes to take a walk")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].tool, "notification")
        self.assertEqual(tasks[0].action, "set_timer")
        self.assertEqual(tasks[0].parameters["seconds"], 900.0)
        self.assertEqual(tasks[0].parameters["message"], "take a walk")

        tasks = planner.plan("remind me in 30 seconds: stretch")
        self.assertEqual(tasks[0].parameters["seconds"], 30.0)
        self.assertEqual(tasks[0].parameters["message"], "stretch")

        tasks = planner.plan("remind me in 1 hour to review PR")
        self.assertEqual(tasks[0].parameters["seconds"], 3600.0)
        self.assertEqual(tasks[0].parameters["message"], "review PR")

        # Set timer ...
        tasks = planner.plan("set a timer for 25 minutes (Pomodoro)")
        self.assertEqual(tasks[0].action, "set_timer")
        self.assertEqual(tasks[0].parameters["seconds"], 1500.0)
        self.assertEqual(tasks[0].parameters["message"], "(Pomodoro)")

        tasks = planner.plan("timer for 45 seconds")
        self.assertEqual(tasks[0].parameters["seconds"], 45.0)

        tasks = planner.plan("timer 5 mins")
        self.assertEqual(tasks[0].parameters["seconds"], 300.0)

        # Notify me ...
        tasks = planner.plan("notify me Deployment complete")
        self.assertEqual(tasks[0].action, "notify")
        self.assertEqual(tasks[0].parameters["message"], "Deployment complete")

        # Timers list and cancel
        tasks = planner.plan("/timers")
        self.assertEqual(tasks[0].action, "list_timers")

        tasks = planner.plan("/cancel-timer 2")
        self.assertEqual(tasks[0].action, "cancel_timer")
        self.assertEqual(tasks[0].parameters["timer_id"], 2)

    @patch("subprocess.run")
    def test_power_manager_profiles_and_throttling(self, mock_run):
        """PowerManager should determine profiles and throttle speculative AI on battery."""
        from system.power_manager import PowerManager
        pm = PowerManager()

        # 1. AC Power connected -> Performance Mode
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="Now drawing from 'AC Power'\n -InternalBattery-0 (id=123)\t100%; charged; present: true\n",
            stderr="",
        )
        pm._cached_status = None
        status = pm.get_power_status()
        self.assertFalse(status["is_on_battery"])
        self.assertEqual(pm.get_active_profile(), PowerManager.PROFILE_PERFORMANCE)
        self.assertFalse(pm.should_throttle_speculative_ai("how are you"))

        # 2. On Battery (50%) -> Balanced Mode
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="Now drawing from 'Battery Power'\n -InternalBattery-0 (id=123)\t50%; discharging; 4:30 remaining present: true\n",
            stderr="",
        )
        pm._cached_status = None
        status = pm.get_power_status()
        self.assertTrue(status["is_on_battery"])
        self.assertEqual(pm.get_active_profile(), PowerManager.PROFILE_BALANCED)
        # Conversational query without action keyword is throttled to keep Mac cool
        self.assertTrue(pm.should_throttle_speculative_ai("hello how are you"))
        # Action query with 'open' or 'create' is NOT throttled
        self.assertFalse(pm.should_throttle_speculative_ai("open chrome"))
        self.assertFalse(pm.should_throttle_speculative_ai("create folder demo"))

        # 3. Low Battery (15%) -> Eco Saver Mode
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="Now drawing from 'Battery Power'\n -InternalBattery-0 (id=123)\t15%; discharging; 0:45 remaining present: true\n",
            stderr="",
        )
        pm._cached_status = None
        self.assertEqual(pm.get_active_profile(), PowerManager.PROFILE_ECO_SAVER)
        self.assertTrue(pm.should_throttle_speculative_ai("open chrome"))

        # 4. Manual override
        pm.set_manual_profile("eco")
        self.assertEqual(pm.get_active_profile(), PowerManager.PROFILE_ECO_SAVER)
        pm.set_manual_profile("auto")

    def test_planner_creates_power_tasks(self):
        """Planner should recognize power mode and eco mode commands."""
        planner = Planner()

        for phrase in ["/power", "/eco", "power mode", "power status", "check power"]:
            tasks = planner.plan(phrase)
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].tool, "system")
            self.assertEqual(tasks[0].action, "power_profile")

        tasks = planner.plan("/eco on")
        self.assertEqual(tasks[0].action, "set_power_profile")
        self.assertEqual(tasks[0].parameters["profile"], "eco")

        tasks = planner.plan("/eco off")
        self.assertEqual(tasks[0].action, "set_power_profile")
        self.assertEqual(tasks[0].parameters["profile"], "auto")

    def test_system_tool_power_profile_execution(self):
        """SystemTool should execute power profile actions."""
        from tools.system_tool import SystemTool
        tool = SystemTool()

        res = tool.execute(Task("system", "power_profile"))
        self.assertTrue(res.success)
        self.assertIn("Power Profile", res.message)
        self.assertIn("profile", res.data)

        res_set = tool.execute(Task("system", "set_power_profile", parameters={"profile": "eco"}))
        self.assertTrue(res_set.success)
        self.assertEqual(res_set.data["profile"], "eco_saver")

        res_reset = tool.execute(Task("system", "set_power_profile", parameters={"profile": "auto"}))
        self.assertTrue(res_reset.success)



