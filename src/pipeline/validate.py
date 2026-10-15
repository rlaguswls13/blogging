from typing import List, Tuple

from src.pipeline.check import (
    SPECIFIC_MARKER_PATTERN,
    TRUSTED_REFERENCE_DOMAINS,
    VAGUE_EVIDENCE_PATTERN,
    check_post,
    quality_gate_errors,
)
from src.pipeline.lint import lint_post
from src.pipeline.validation_common import load_validation_input, parse_fact_check_claims, section_text


def validate_run(
    run_id: str,
    require_human_approval: bool = True,
    skip_link_check: bool = False,
) -> Tuple[bool, List[str], List[str]]:
    context = load_validation_input(run_id)
    lint_errors, warnings = lint_post(context.post, context.gate, skip_link_check)
    errors = [*lint_errors, *check_post(context.post)]
    if require_human_approval and context.gate.requireHumanApproval and not context.state.humanApproved:
        errors.append("state.json의 humanApproved가 true가 아닙니다.")
    return not errors, errors, warnings


__all__ = [
    "SPECIFIC_MARKER_PATTERN",
    "TRUSTED_REFERENCE_DOMAINS",
    "VAGUE_EVIDENCE_PATTERN",
    "parse_fact_check_claims",
    "quality_gate_errors",
    "section_text",
    "validate_run",
]
