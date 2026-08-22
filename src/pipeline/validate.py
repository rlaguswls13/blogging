import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse
import frontmatter
import requests
from src.core.paths import run_directory, gate_path
from src.core.files import read_json, read_state
from src.core.types import ArticleFrontmatter, PublishGate

# Tier 1/2 참고문헌 신뢰도 도메인 allowlist (wiki/Blog_Writing_Rules.md 10번 수칙 참고).
# 2026-08-22: 이 목록과 하나도 겹치지 않으면 예전엔 경고만 띄우고 통과시켰으나, 경고가 무시되고
# 넘어가는 사례가 반복돼(사용자 요청) 오류로 승격했다 — 발행을 막는다.
TRUSTED_REFERENCE_DOMAINS = {
    "arxiv.org", "dl.acm.org", "ieeexplore.ieee.org", "datatracker.ietf.org",
    "www.w3.org", "w3.org", "docs.oracle.com", "spring.io", "docs.spring.io",
    "kubernetes.io", "kafka.apache.org", "redis.io", "www.cncf.io", "cncf.io",
    "www.linuxfoundation.org", "linuxfoundation.org", "developer.mozilla.org",
    "learn.microsoft.com", "cloud.google.com", "docs.aws.amazon.com", "aws.amazon.com",
    "man7.org", "kernel.org", "www.kernel.org", "openjdk.org", "docs.python.org",
    "modelcontextprotocol.io", "blog.modelcontextprotocol.io",
    "www.rfc-editor.org", "rfc-editor.org", "www.ietf.org", "ietf.org",
    # 2026-08-22: reference_credibility_tier가 warning->error로 승격되면서 이 목록에 없는
    # 도메인만 쓰면 발행이 막히게 됐다. 누적 누락 지적 반영(session-handoff 2026-08-19 이후).
    "grpc.io", "protobuf.dev", "projectreactor.io", "docs.confluent.io",
    "cassandra.apache.org", "go.dev", "github.com", "dev.mysql.com", "www.postgresql.org",
    "postgresql.org",
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

# 내부링크(같은 블로그 소속 다른 글) 판별용 도메인. wiki/Blog_Writing_Rules.md 15번 수칙 참고.
INTERNAL_LINK_DOMAIN = "beji-tech.blogspot.com"

def internal_link_count(text: str) -> int:
    """마크다운 링크 중 자사 블로그 도메인(다른 발행 글)을 가리키는 개수를 센다."""
    urls = re.findall(r"\[[^\]]*\]\((https?://[^)]+)\)", text)
    return sum(1 for url in urls if INTERNAL_LINK_DOMAIN in url)

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

    # Check Reference Credibility Tier (2026-08-22: warning -> error 승격)
    live_urls = [url for _, url in ref_urls if url]
    if live_urls:
        has_trusted = any(
            urlparse(url).netloc in TRUSTED_REFERENCE_DOMAINS for url in live_urls
        )
        if not has_trusted:
            errors.append(
                "참고문헌이 전부 비공식/블로그성 출처입니다. 공식 문서나 논문을 최소 1개 포함해야 합니다."
            )

    # Check Section Minimum Word Counts
    for section, min_words in gate.sectionMinWords.items():
        text = section_text(post.content, section)
        actual = word_count(text)
        if actual < min_words:
            errors.append(
                f"'{section}' 섹션 분량이 부족합니다. 최소 {min_words}단어 필요, 현재 약 {actual}단어입니다."
            )

    # Check Code/Image Presence (2026-08-22: warning -> error 승격)
    if code_block_count(post.content) == 0 and image_count(post.content) == 0:
        errors.append("코드 예시와 이미지가 모두 없습니다. 최소 1개는 포함해야 합니다.")

    # Check Internal Link Count (2026-08-22: warning -> error 승격)
    # '## 백링크' 섹션이 예전엔 라이브 HTML에서 통째로 삭제돼 내부링크가 전혀 렌더링되지 않았다
    # (converter.py 버그, 이번에 수정). 이제 실제로 라이브에 노출되므로 최소 개수를 강제한다.
    # 신규 주제의 첫 글처럼 아직 연결할 기존 글이 없다면, 다른 이미 발행된 관련 글을 찾아 연결할 것
    # (완전히 새 카테고리라 정말 하나도 없다면 wiki/Post_Topic_Backlog.md에 먼저 관련 글을 채택할 것).
    internal_link_text = "\n".join(
        section_text(post.content, s) for s in ("본문", "백링크", "종합적 의견")
    )
    internal_links = internal_link_count(internal_link_text)
    if internal_links < gate.minimumInternalLinks:
        errors.append(
            f"자사 블로그 내부링크가 {internal_links}개뿐입니다(최소 {gate.minimumInternalLinks}개 필요). "
            "관련 발행 글을 '## 백링크' 또는 본문에 실제 라이브 URL로 링크해야 합니다."
        )

    # Check Opinion Disclaimer
    # 2026-08-22: 예전엔 정확히 동일한 리터럴 문장("사실 전달이 아니라 작성자의 해석과 견해...")을
    # 요구했는데, 그 결과 47개 발행 글 전체에 토씨 하나 안 틀린 문장이 반복돼 "대량생산 콘텐츠" 신호를
    # 스스로 만들고 있었다(wiki/Blog_Writing_Rules.md 14/15번 수칙 참고). 이제는 "작성자의 견해"/
    # "종합적 의견" 섹션에 의견-공지 취지의 인용구(`>`)가 존재하는지만 구조적으로 확인하고, 문구 자체는
    # 매번 자기 말로 다르게 쓰도록 허용한다.
    if gate.requireOpinionDisclaimer:
        disclaimer_pattern = re.compile(r"^>.*(의견|견해|해석|사견)", re.MULTILINE)
        for section in ("작성자의 견해", "종합적 의견"):
            section_body = section_text(post.content, section)
            if not disclaimer_pattern.search(section_body):
                errors.append(
                    f"'{section}' 섹션에 의견/해석임을 밝히는 인용구(`>`) 안내문이 없습니다."
                )

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

    # Check for claims with no evidence cited (anti-hallucination signal, 2026-08-22: warning -> error 승격)
    unsupported = [claim.strip() for claim, verdict, evidence in claim_rows if not evidence.strip()]
    if unsupported:
        errors.append(
            f"근거(출처) 없이 판정된 claim이 {len(unsupported)}건 있습니다: {unsupported[0][:60]}"
        )
        
    # Check Human Approval
    if require_human_approval and gate.requireHumanApproval and not state.humanApproved:
        errors.append("state.json의 humanApproved가 true가 아닙니다.")
        
    # Return formatted result
    return len(errors) == 0, errors, warnings
