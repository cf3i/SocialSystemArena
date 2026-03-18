"""Benchmark integrations."""

from .pinchbench import (
    PinchBenchRunConfig,
    PinchGradeResult,
    PinchTask,
    grade_pinch_task_automated,
    load_pinch_tasks,
    run_pinchbench,
    select_pinch_tasks,
)
from .multiagentbench import (
    MultiAgentBenchGradeResult,
    MultiAgentBenchRunConfig,
    MultiAgentBenchTask,
    grade_multiagent_database,
    load_multiagent_tasks,
    run_multiagentbench,
    select_multiagent_tasks,
)
from .clawebench import (
    ClawBenchRunConfig,
    ClawGradeResult,
    ClawTask,
    load_claw_tasks,
    run_clawebench,
    select_claw_tasks,
    task_needs_judge,
)

__all__ = [
    "PinchBenchRunConfig",
    "PinchGradeResult",
    "PinchTask",
    "grade_pinch_task_automated",
    "load_pinch_tasks",
    "run_pinchbench",
    "select_pinch_tasks",
    "MultiAgentBenchRunConfig",
    "MultiAgentBenchGradeResult",
    "MultiAgentBenchTask",
    "grade_multiagent_database",
    "load_multiagent_tasks",
    "run_multiagentbench",
    "select_multiagent_tasks",
    "ClawBenchRunConfig",
    "ClawGradeResult",
    "ClawTask",
    "load_claw_tasks",
    "run_clawebench",
    "select_claw_tasks",
    "task_needs_judge",
]
