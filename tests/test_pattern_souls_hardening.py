from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
PATTERN_ROOT = ROOT / "systems" / "pattern_souls"


# Keep this mapping aligned with mas_engine.core.runtime._PATTERN_STAGE_ALIAS.
ALIAS_GROUPS = {
    "pipeline": {
        "planner.md": ["plan.md"],
        "executor.md": ["execute.md"],
    },
    "gated_pipeline": {
        "planner.md": ["draft.md"],
        "gate.md": ["review.md"],
        "executor.md": ["execute.md"],
    },
    "autonomous_cluster": {
        "orchestrator.md": ["orchestrate.md"],
        "cluster.md": ["cluster_exec.md"],
        "auditor.md": ["audit.md"],
    },
    "consensus": {
        "planner.md": ["propose.md"],
        "consensus.md": ["vote.md"],
        "executor.md": ["execute.md"],
    },
}


REQUIRED_SECTIONS = [
    "任务上下文:",
    "模式定位（默认规则）:",
    "硬规则:",
    "决策策略:",
    "建议输出:",
]


INSTITUTION_TOKENS = [
    "雅典",
    "秦汉",
    "唐代",
    "门下省",
    "苏联",
    "美国联邦",
    "蒙古",
    "江户",
    "幕府",
]


class PatternSoulsHardeningTests(unittest.TestCase):
    def _iter_soul_templates(self) -> list[Path]:
        return [
            p
            for p in sorted(PATTERN_ROOT.rglob("*.md"))
            if p.parent != PATTERN_ROOT
        ]

    def test_alias_files_are_byte_identical(self) -> None:
        for pattern, mapping in ALIAS_GROUPS.items():
            base = PATTERN_ROOT / pattern
            for canonical, aliases in mapping.items():
                canonical_path = base / canonical
                self.assertTrue(canonical_path.exists(), f"missing {canonical_path}")
                canonical_text = canonical_path.read_text(encoding="utf-8")
                for alias in aliases:
                    alias_path = base / alias
                    self.assertTrue(alias_path.exists(), f"missing {alias_path}")
                    alias_text = alias_path.read_text(encoding="utf-8")
                    self.assertEqual(
                        alias_text,
                        canonical_text,
                        f"alias drift: {alias_path} != {canonical_path}",
                    )

    def test_pattern_souls_have_required_structure(self) -> None:
        for path in self._iter_soul_templates():
            text = path.read_text(encoding="utf-8")
            for section in REQUIRED_SECTIONS:
                self.assertIn(section, text, f"{path} missing section: {section}")
            self.assertIn(
                "若 Institution SOP 有冲突，以 Institution SOP 为准。",
                text,
                f"{path} missing precedence statement",
            )
            self.assertIn("- summary:", text, f"{path} missing summary output key")
            self.assertIn("decision", text, f"{path} missing decision constraints")

    def test_pattern_souls_avoid_institution_specific_terms(self) -> None:
        for path in self._iter_soul_templates():
            text = path.read_text(encoding="utf-8")
            for token in INSTITUTION_TOKENS:
                self.assertNotIn(
                    token,
                    text,
                    f"{path} should stay pattern-generic but contains institution token: {token}",
                )

    def test_consensus_vote_stage_is_ballot_only(self) -> None:
        for path in [
            PATTERN_ROOT / "consensus" / "consensus.md",
            PATTERN_ROOT / "consensus" / "vote.md",
        ]:
            text = path.read_text(encoding="utf-8")
            self.assertIn("decision 只能是 yes 或 no", text, f"{path} must restrict vote decision")
            self.assertIn(
                "不得输出 approve/reject/next/dispute/invalidate",
                text,
                f"{path} must block non-ballot route decisions",
            )
