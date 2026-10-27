class ConfirmationManager:
    """Records an explicit user confirmation on one structured task.

    Sprint 12.1 adds a staging slot so that natural-language phrases
    like "yes" can confirm only the single task currently awaiting
    confirmation, without letting arbitrary chat trigger execution.
    """

    def __init__(self):
        self._staged_task = None

    # --- Legacy interface (Sprint 12.0, preserved) ---

    def confirm(self, task):
        task.parameters["confirmed"] = True
        return task

    # --- Staging interface (Sprint 12.1) ---

    def stage(self, task):
        """Stage exactly one task as the pending confirmation target."""
        self._staged_task = task
        return task

    def confirm_staged(self):
        """Confirm the staged task and clear the slot.

        Returns the confirmed task, or None if nothing is staged.
        """
        task = self._staged_task
        if task is None:
            return None

        self._staged_task = None
        return self.confirm(task)

    def cancel_staged(self):
        """Clear the staged slot without confirming.

        Returns the previously staged task, or None.
        """
        task = self._staged_task
        self._staged_task = None
        return task

    @property
    def pending_task(self):
        """The currently staged task, or None."""
        return self._staged_task

    @property
    def has_pending(self):
        """True if a task is staged for confirmation."""
        return self._staged_task is not None
