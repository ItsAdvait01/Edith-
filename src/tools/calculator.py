from tools.base_tool import BaseTool
from brain.action_result import ActionResult
from brain.task import Task


class Calculator(BaseTool):

    NAME = "calculator"
    DESCRIPTION = "Evaluates a calculator expression."
    RESOURCE_PROFILE = "on_demand"
    SUPPORTED_ACTIONS = frozenset({"calculate"})

    def can_handle(self, user_input):

        operators = ["+", "-", "*", "/", "%", "**"]

        return any(op in user_input for op in operators)

    def task_from_legacy_input(self, user_input):

        return Task(tool=self.NAME, action="calculate", target=user_input)

    def execute(self, task):

        if task.action != "calculate":
            return ActionResult(
                success=False,
                message=f"The calculator tool cannot {task.action}.",
                error="unsupported_action",
            )

        try:
            value = str(eval(task.target))
            return ActionResult(
                success=True,
                message=value,
                data={"value": value},
            )
        except Exception as error:
            return ActionResult(
                success=False,
                message="I could not calculate that expression.",
                error=str(error),
            )
