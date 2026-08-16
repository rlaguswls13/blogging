import re
from typing import List, Optional, Tuple
import frontmatter
import requests
from src.core.paths import run_directory, gate_path
from src.core.files import read_json, read_state
from src.core.types import ArticleFrontmatter, PublishGate

def section_exists(body: str, heading: str) -> bool:
    escaped = re.escape(heading)
    pattern = re.compile(rf"^##\s+{escaped}\s*$", re.MULTILINE)
    return bool(pattern.search(body))

def reference_section_items(body: str) -> List[str]:
    match = re.search(r"^##\s+참고문헌\s*$(.*?)(?=^##|\Z)", body, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    section_content = match.group(1)
    return re.findall(r"^[ \t]*(?:\d+\.|-)[ \t]+(.+)$", section_content, re.MULTILINE)

def reference_count(body: str) -> int:
    return len(reference_section_items(body))

def reference_urls(items: List[str]) -> List[Tuple[str, Optional[str]]]:
    """참고문헌 리스트 항목별로 (원문, URL 또는 None)을 반환한다."""
    results = []
    for item in items:
        url_match = re.search(r"https?://[^\s)>\]]+", item)
        results.append((item.strip(), url_match.group(0) if url_match else None))
    return results

def check_link_liveness(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """URL이 살아있는지 확인한다. HEAD가 거부되면 GET으로 재시도한다."""
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            resp = requests.get(url, timeout=timeout, stream=True)
        return resp.status_code < 400, f"HTTP {resp.status_code}"
    except requests.RequestException as e:
        return False, str(e)

def validate_run(
    run_id: str,
    require_human_approval: bool = True,
    skip_link_check: bool = False
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
    ref_items = reference_section_items(post.content)
    refs = len(ref_items)
    if refs < gate.minimumReferences:
        errors.append(f"참고문헌은 최소 {gate.minimumReferences}개가 필요합니다. 현재 {refs}개입니다.")

    # Check Reference Link Validity (missing URL / broken link)
    if not skip_link_check:
        for item, url in reference_urls(ref_items):
            if url is None:
                message = f"참고문헌에 URL이 없습니다: {item[:60]}"
                (errors if not gate.allowBrokenLinks else warnings).append(message)
                continue
            ok, detail = check_link_liveness(url)
            if not ok:
                message = f"참고문헌 링크가 접속되지 않습니다 ({detail}): {url}"
                (errors if not gate.allowBrokenLinks else warnings).append(message)

    # Check Opinion Disclaimer
    if gate.requireOpinionDisclaimer:
        if not re.search(r"^>.*사실 전달이 아니라 작성자의 해석과 견해", post.content, re.MULTILINE):
            errors.append("작성자의 견해 안내문이 인용구(`>`) 형식으로 되어 있지 않습니다.")

    # Check for encoding corruption (mojibake)
    if "�" in post.content:
        errors.append("본문에 깨진 문자(U+FFFD)가 포함되어 있습니다. 인코딩을 확인하세요.")

    # Check High-Risk / Unverified Claims
    if re.search(r"\bRisk:\s*high[\s\S]{0,250}\bVerdict:\s*unverified\b", post.content, re.IGNORECASE):
        errors.append("고위험 미검증 주장이 남아 있습니다.")
        
    # Check Contradicted Claims
    if re.search(r"\bVerdict:\s*contradicted\b", post.content, re.IGNORECASE):
        errors.append("반박된 주장이 남아 있습니다.")
        
    # Check Human Approval
    if require_human_approval and gate.requireHumanApproval and not state.humanApproved:
        errors.append("state.json의 humanApproved가 true가 아닙니다.")
        
    # Return formatted result
    return len(errors) == 0, errors, warnings
