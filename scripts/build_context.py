#!/usr/bin/env python3
"""
build_context.py - 根据当前 stage 输出需要加载的文件列表

用法：
    python scripts/build_context.py --stage <stage_id>

输出：
    每行一个文件路径（stdout）；缺少必须文件时 exit 1

Agent 使用方式：
    1. 读 docs/stage.lock，获取 current 字段
    2. 运行 python scripts/build_context.py --stage <current>
    3. 读取输出的所有文件
    4. 执行 docs/workflow/<current>.md 的指令
"""

import argparse
import os
import sys
import yaml

# ─────────────────────────────────────────────
# 全局层：所有 Stage 都注入（必须存在）
# ─────────────────────────────────────────────
GLOBAL_FILES = [
    "docs/overview.md",
    "docs/architecture.md",
    "docs/conventions.md",
    "issue_test/README.md",
]

# ─────────────────────────────────────────────
# 可选全局层：存在才注入，缺失不报错
# ─────────────────────────────────────────────
OPTIONAL_GLOBAL_FILES = [
    "docs/wisdom.md",
    "docs/antipatterns.md",
]

# ─────────────────────────────────────────────
# Stage 层：按 Stage 单独注入（必须存在的文件）
# ─────────────────────────────────────────────
STAGE_FILES = {
    "stage1": [
        "docs/stage.lock",
        "docs/progress.md",
        "docs/blockers.md",
        "docs/plan/current.md",
    ],
    "stage2": [
        "docs/plan/backlog.md",
        "docs/decisions.md",
    ],
    "stage3": [
        "docs/plan/current.md",
        "docs/security.md",
    ],
    "stage4": [
        "docs/plan/current.md",
        "docs/quality.md",
    ],
    "stage5": [
        "docs/decisions.md",
        # archive/<issue_id>.md 动态注入，见下方逻辑
    ],
    "stage6": [
        "docs/progress.md",
        "docs/decisions.md",
    ],
}

# ─────────────────────────────────────────────
# 指令层：每个 Stage 对应的执行指令文件（必须存在）
# ─────────────────────────────────────────────
STAGE_INSTRUCTION = {
    "stage1": "docs/workflow/stage1.md",
    "stage2": "docs/workflow/stage2.md",
    "stage3": "docs/workflow/stage3.md",
    "stage4": "docs/workflow/stage4.md",
    "stage5": "docs/workflow/stage5.md",
    "stage6": "docs/workflow/stage6.md",
}

VALID_STAGES = list(STAGE_FILES.keys())


def get_repo_root():
    """从脚本位置推断仓库根目录"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def read_stage_lock(repo_root):
    """读取 stage.lock，返回 dict"""
    lock_path = os.path.join(repo_root, "docs", "stage.lock")
    if not os.path.exists(lock_path):
        return {}
    with open(lock_path, "r") as f:
        return yaml.safe_load(f) or {}


def resolve_files(stage, repo_root, lock_data):
    """
    按顺序组装文件列表：
    1. 全局层（必须）
    2. 可选全局层（存在才加，缺失跳过）
    3. Stage 层（必须）
    4. Stage 5 动态 archive 文件（必须，缺失则 fatal）
    5. 指令层（必须）

    返回 (required_files, optional_files) 两个列表。
    required_files 中的每个文件若缺失则脚本以 exit 1 终止。
    """
    required = []
    optional = []

    # 1. 全局层（必须）
    required.extend(GLOBAL_FILES)

    # 2. 可选全局层
    for f in OPTIONAL_GLOBAL_FILES:
        if os.path.exists(os.path.join(repo_root, f)):
            optional.append(f)

    # 3. Stage 层（必须）
    required.extend(STAGE_FILES.get(stage, []))

    # 3.5 Stage 3/4 当前 issue 的回归脚本（必须）
    if stage in {"stage3", "stage4"}:
        issue_id = (lock_data.get("meta") or {}).get("issue_id")
        if issue_id:
            required.append(f"issue_test/{issue_id}.sh")
        else:
            print(
                f"[build_context] FATAL: {stage} but meta.issue_id is null in stage.lock",
                file=sys.stderr,
            )
            sys.exit(1)

    # 4. Stage 5/6 动态注入 archive 文件（必须）
    if stage in {"stage5", "stage6"}:
        issue_id = (lock_data.get("meta") or {}).get("issue_id")
        if issue_id:
            required.append(f"docs/plan/archive/{issue_id}.md")
        else:
            print(
                f"[build_context] FATAL: {stage} but meta.issue_id is null in stage.lock",
                file=sys.stderr,
            )
            sys.exit(1)

    # 5. 指令层（必须）
    instruction_file = STAGE_INSTRUCTION.get(stage)
    if instruction_file:
        required.append(instruction_file)

    return required, optional


def main():
    parser = argparse.ArgumentParser(
        description="根据当前 stage 输出需要加载的文件列表"
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=VALID_STAGES,
        help=f"当前 stage ID，可选值：{', '.join(VALID_STAGES)}",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    lock_data = read_stage_lock(repo_root)
    required, optional = resolve_files(args.stage, repo_root, lock_data)

    # 必须文件：缺失则报错并 exit 1
    missing = [f for f in required if not os.path.exists(os.path.join(repo_root, f))]
    if missing:
        for f in missing:
            print(f"[build_context] FATAL: required file missing: {f}", file=sys.stderr)
        sys.exit(1)

    # 输出所有文件（必须 + 可选）
    for f in required + optional:
        print(f)


if __name__ == "__main__":
    main()
