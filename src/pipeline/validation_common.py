import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

import frontmatter

from src.core.files import read_json, read_state
from src.core.paths import gate_path, run_directory
from src.core.types import PublishGate


@dataclass(frozen=True, slots=True)
class ValidationInput:
    run_dir: Path
    state: Any
    gate: PublishGate
    post: Any


def load_validation_input(run_id: str) -> ValidationInput:
    run_dir = run_directory(run_id)
    state = read_state(run_dir / "state.json")
    gate = PublishGate.model_validate(read_json(gate_path))
    with open(run_dir / "final.md", "r", encoding="utf-8") as source:
        post = frontmatter.load(source)
    return ValidationInput(run_dir, state, gate, post)


def section_exists(body: str, heading: str) -> bool:
    return bool(re.search(rf"^##\s+{re.escape(heading)}\s*$", body, re.MULTILINE))


def section_text(body: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##(?!#)|\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def word_count(text: str) -> int:
    return len(re.findall(r"[가-힣]", text)) + len(re.findall(r"[A-Za-z0-9]+", text))


def parse_fact_check_claims(body: str) -> List[Tuple[str, str, str]]:
    return re.findall(
        r"^\|(?!\s*Claim\s*\|)(?!\s*-+\s*\|)(.+?)\|\s*(verified|unverified|contradicted)\s*\|(.*?)\|\s*$",
        section_text(body, "사실 검증 결과"),
        re.IGNORECASE | re.MULTILINE,
    )


def reference_section_items(body: str) -> List[str]:
    section = section_text(body, "참고문헌")
    return re.findall(r"^[ \t]*(?:\d+\.|-)[ \t]+(.+)$", section, re.MULTILINE)


def reference_urls(items: List[str]) -> List[Tuple[str, Optional[str]]]:
    results = []
    for item in items:
        match = re.search(r"https?://[^\s)>\]]+", item)
        results.append((item.strip(), match.group(0) if match else None))
    return results


def internal_link_count(text: str) -> int:
    urls = re.findall(r"\[.*?\]\((https?://[^)]+)\)", text)
    return sum(1 for url in urls if "beji-tech.blogspot.com" in url)
