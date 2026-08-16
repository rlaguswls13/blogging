import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse
import frontmatter
import requests
from src.core.paths import run_directory, gate_path
from src.core.files import read_json, read_state
from src.core.types import ArticleFrontmatter, PublishGate

# Tier 1/2 참고문헌 신뢰도 도메인 allowlist (wiki/Blog_Writing_Rules.md 10번 수칙 참고).
# 이 목록과 하나도 겹치지 않으면 "출처가 전부 블로그성"이라는 경고만 띄운다(발행 차단 아님).
TRUSTED_REFERENCE_DOMAINS = {
    "arxiv.org", "dl.acm.org", "ieeexplore.ieee.org", "datatracker.ietf.org",
    "www.w3.org", "w3.org", "docs.oracle.com", "spring.io", "docs.spring.io",
    "kubernetes.io", "kafka.apache.org", "redis.io", "www.cncf.io", "cncf.io",
    "www.linuxfoundation.org", "linuxfoundation.org", "developer.mozilla.org",
    "learn.microsoft.com", "cloud.google.com", "docs.aws.amazon.com", "aws.amazon.com",
    "man7.org", "kernel.org", "www.kernel.org", "openjdk.org", "docs.python.org",
    "modelcontextprotocol.io", "blog.modelcontextprotocol.io",
    "www.rfc-editor.org", "rfc-editor.org", "www.ietf.org", "ietf.org",
}

def section_exists(body: str, heading: str) -> bool:
    escaped = re.escape(heading)
    pattern = re.compile(rf"^##\s+{escaped}\s*$", re.MULTILINE)
    return bool(pattern.search(body))

def section_text(body: str, heading: str) -> str:
    # (?=^##(?!#)|\Z): 다음 H2(##)에서 멈추되, 본문 안에 흔한 H3(###) 하위 소제목까지
    # section 끝으로 잘못 인식하지 않도록 3번째 #이 없는 경우만 경계로 취급한다.
    escaped = re.escape(heading)
    pattern = re.compile(rf"^##\s+{escaped}\s*$(.*?)(?=^##(?!#)|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(body)
    return match.group(1) if match else ""

def word_count(text: str) -> int:
    """한글 글자 수 + 영숫자 단어 수를 더한 대략적인 분량 지표."""
    cjk = len(re.findall(r"[가-힣]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk + latin_words

def code_block_count(body: str) -> int:
    return len(re.findall(r"```", body)) // 2

def image_count(body: str) -> int:
    return len(re.findall(r"!\[[^\]]*\]\([^)]+\)", body))

def reference_section_items(body: str) -> List[str]:
    match = re.search(r"^##\s+참고문헌\s*$(.*?)(?=^##(?!#)|\Z)", body, re.MULTILINE | re.DOTALL)
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

_LINK_CHECK_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ai-blogging-linkcheck/1.0)"}

def check_link_liveness(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """URL이 살아있는지 확인한다. HEAD가 거부되면 GET으로 재시도한다.

    User-Agent를 지정하지 않으면 Wikipedia 등 일부 사이트가 자동화 요청으로 보고
    403을 돌려줘 실제로는 살아있는 링크가 깨진 것으로 오탐되므로 브라우저 UA를 붙인다.
    """
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True, headers=_LINK_CHECK_HEADERS)
        if resp.status_code >= 400:
            resp = requests.get(url, timeout=timeout, stream=True, headers=_LINK_CHECK_HEADERS)
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
    ref_urls = reference_urls(ref_items)
    if not skip_link_check:
        for item, url in ref_urls:
            if url is None:
                message = f"참고문헌에 URL이 없습니다: {item[:60]}"
                (errors if not gate.allowBrokenLinks else warnings).append(message)
                continue
            ok, detail = check_link_liveness(url)
            if not ok:
                message = f"참고문헌 링크가 접속되지 않습니다 ({detail}): {url}"
                (errors if not gate.allowBrokenLinks else warnings).append(message)

    # Check Reference Credibility Tier (warning only)
    live_urls = [url for _, url in ref_urls if url]
    if live_urls:
        has_trusted = any(
            urlparse(url).netloc in TRUSTED_REFERENCE_DOMAINS for url in live_urls
        )
        if not has_trusted:
            warnings.append(
                "참고문헌이 전부 비공식/블로그성 출처입니다. 공식 문서나 논문을 최소 1개 포함하는 것을 권장합니다."
            )

    # Check Section Minimum Word Counts
    for section, min_words in gate.sectionMinWords.items():
        text = section_text(post.content, section)
        actual = word_count(text)
        if actual < min_words:
            errors.append(
                f"'{section}' 섹션 분량이 부족합니다. 최소 {min_words}단어 필요, 현재 약 {actual}단어입니다."
            )

    # Check Code/Image Presence (warning only)
    if code_block_count(post.content) == 0 and image_count(post.content) == 0:
        warnings.append("코드 예시와 이미지가 모두 없습니다. 주제에 맞다면 추가를 고려하세요.")

    # Check Opinion Disclaimer
    if gate.requireOpinionDisclaimer:
        if not re.search(r"^>.*사실 전달이 아니라 작성자의 해석과 견해", post.content, re.MULTILINE):
            errors.append("작성자의 견해 안내문이 인용구(`>`) 형식으로 되어 있지 않습니다.")

    # Check for encoding corruption (mojibake)
    if "�" in post.content:
        errors.append("본문에 깨진 문자(U+FFFD)가 포함되어 있습니다. 인코딩을 확인하세요.")

    # Check Unverified / Contradicted Claims
    # 실제 저작 포맷은 "| Claim | 판정 | 근거 |" 표에 verified/unverified/contradicted가
    # 표 셀 값으로 들어간다("Risk: high"/"Verdict: unverified" 같은 접두 표기는 실제로
    # 쓰인 적이 없어 예전 정규식이 항상 무매칭이었다 — 2026-08-17 확인).
    fact_check_section = section_text(post.content, "사실 검증 결과")
    claim_rows = re.findall(
        r"^\|(?!\s*Claim\s*\|)(?!\s*-+\s*\|)(.+?)\|\s*(verified|unverified|contradicted)\s*\|(.*?)\|\s*$",
        fact_check_section, re.IGNORECASE | re.MULTILINE
    )
    verdicts = [v.lower() for _claim, v, _evidence in claim_rows]
    if "unverified" in verdicts:
        errors.append("미검증(unverified) 판정의 주장이 남아 있습니다.")
    if "contradicted" in verdicts:
        errors.append("반박된(contradicted) 판정의 주장이 남아 있습니다.")

    # Check for claims with no evidence cited (weak anti-hallucination signal, warning only)
    unsupported = [claim.strip() for claim, verdict, evidence in claim_rows if not evidence.strip()]
    if unsupported:
        warnings.append(
            f"근거(출처) 없이 판정된 claim이 {len(unsupported)}건 있습니다: {unsupported[0][:60]}"
        )
        
    # Check Human Approval
    if require_human_approval and gate.requireHumanApproval and not state.humanApproved:
        errors.append("state.json의 humanApproved가 true가 아닙니다.")
        
    # Return formatted result
    return len(errors) == 0, errors, warnings
