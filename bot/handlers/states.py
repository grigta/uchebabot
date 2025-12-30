"""FSM states for EduHelper Bot."""

from aiogram.fsm.state import State, StatesGroup


class TaskFlow(StatesGroup):
    """States for task processing flow."""

    # User is answering interview questions
    interview = State()

    # User is confirming/modifying plan
    awaiting_plan = State()

    # User is modifying the plan
    modifying_plan = State()

    # AI is processing the task
    processing = State()
