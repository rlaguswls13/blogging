import re
from typing import List, Tuple
import frontmatter
from src.core.paths import run_directory, gate_path
from src.core.files import read_json, read_state
from src.core.types import ArticleFrontmatter, PublishGate

def section_exists(body: str, heading: str) -> bool:
    escaped = re.escape(heading)
    pattern = re.compile(rf"^##\s+{escaped}\s*$", re.MULTILINE)
    return bool(pattern.search(body))

def reference_count(body: str) -> int:
    match = re.search(r"^##\s+참고문헌\s*$(.*?)(?=^##|\Z)", body, re.MULTILINE | re.DOTALL)
    if not match:
        return 0
    section_content = match.group(1)
    items = re.findall(r"^[ \t]*(?:\d+\.|-)[ \t]+\S+", section_content, re.MULTILINE)
    return len(items)

def validate_run(
    run_id: str,
    require_human_approval: bool = True
) -> Tuple[bool, List[str], List[str]]:
    dir_path = run_directory(run_id)
    state = read_state(dir_path / "state.json")
    
    gate_data = read_json(gate_path)
    gate = PublishGate.model_validate(gate_data)
    
    with open(dir_path / "final.md", "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
        
    errors = []
    warnings = []
    
    # Validate Frontmatter
    try:
        ArticleFrontmatter.model_validate(post.metadata)
    except Exception as e:
        errors.append(f"frontmatter validation error: {str(e)}")
        
    # Check Required Sections
    for section in gate.requiredSections:
        if not section_exists(post.content, section):
            errors.append(f"필수 섹션이 없습니다: {section}")
            
    # Check Reference Count
    refs = reference_count(post.content)
    if refs < gate.minimumReferences:
        errors.append(f"참고문헌은 최소 {gate.minimumReferences}개가 필요합니다. 현재 {refs}개입니다.")
        
    # Check Opinion Disclaimer
    if gate.requireOpinionDisclaimer:
        if "사실 전달이 아니라 작성자의 해석과 견해" not in post.content:
            errors.append("작성자의 견해 안내문이 없습니다.")
            
    # Check High-Risk / Unverified Claims
    if re.search(r"\bRisk:\s*high[\s\S]{0,250}\bVerdict:\s*unverified\b", post.content, re.IGNORECASE):
        errors.append("고위험 미검증 주장이 남아 있습니다.")
        
    # Check Contradicted Claims
    if re.search(r"\bVerdict:\s*contradicted\b", post.content, re.IGNORECASE):
        errors.append("반박된 주장이 남아 있습니다.")
        
    # Check Human Approval
    if require_human_approval and gate.requireHumanApproval and not state.humanApproved:
        errors.append("state.json의 humanApproved가 true가 아닙니다.")
        
    # Warnings: check urls count against reference count
    urls = re.findall(r"https?://[^\s)>]+", post.content)
    if len(urls) < refs:
        warnings.append("일부 참고문헌에 URL이 없을 수 있습니다.")
        
    # Return formatted result
    return len(errors) == 0, errors, warnings
