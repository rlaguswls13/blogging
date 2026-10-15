import re
from typing import List, Tuple
from urllib.parse import urlparse

from src.pipeline.validation_common import (
    load_validation_input,
    parse_fact_check_claims,
    reference_section_items,
    reference_urls,
    section_text,
)


VAGUE_EVIDENCE_PATTERN = re.compile(r"업계\s*리포트|일반적으로\s*알려진|널리\s*알려진\s*사실|다수의\s*출처|여러\s*자료|^교차\s*확인$")
SPECIFIC_MARKER_PATTERN = re.compile(r"https?://|RFC\s*\d+|공식\s*(문서|블로그|가이드)|[A-Za-z][\w.-]+\.(io|com|org|net|dev)")
TRUSTED_REFERENCE_DOMAINS = {
    "arxiv.org", "dl.acm.org", "ieeexplore.ieee.org", "datatracker.ietf.org", "www.w3.org", "w3.org",
    "docs.oracle.com", "spring.io", "docs.spring.io", "kubernetes.io", "kafka.apache.org", "redis.io",
    "www.cncf.io", "cncf.io", "www.linuxfoundation.org", "linuxfoundation.org", "developer.mozilla.org",
    "learn.microsoft.com", "cloud.google.com", "docs.aws.amazon.com", "aws.amazon.com", "man7.org",
    "kernel.org", "www.kernel.org", "openjdk.org", "docs.python.org", "modelcontextprotocol.io",
    "blog.modelcontextprotocol.io", "www.rfc-editor.org", "rfc-editor.org", "www.ietf.org", "ietf.org",
    "grpc.io", "protobuf.dev", "projectreactor.io", "docs.confluent.io", "cassandra.apache.org", "go.dev",
    "github.com", "dev.mysql.com", "www.postgresql.org", "postgresql.org",
}


def quality_gate_errors(post) -> List[str]:
    from src.tools.check_backlink_relevance import DEFAULT_THRESHOLD as BACKLINK_THRESHOLD, load_url_index, relevance_score, tokenize as backlink_tokenize
    from src.tools.check_code_blocks import SYNTAX_CHECKERS, extract_code_blocks
    from src.tools.check_topic_duplication import DEFAULT_THRESHOLD as TOPIC_THRESHOLD, SERIES_THRESHOLD, dice_score, load_candidates, shares_series_tag, tokenize as topic_tokenize

    errors: List[str] = []
    title = post.metadata.get("title", "")
    tags = [tag for tag in post.metadata.get("tags", []) if isinstance(tag, str)]
    for language, code, _context in extract_code_blocks(post.content):
        checker = SYNTAX_CHECKERS.get(language)
        error = checker(code) if checker else None
        if error:
            errors.append(f"코드 블록({language}) 구문 오류: {error}")

    links = re.findall(r"\[.*?\]\((https?://[^)]+)\)", section_text(post.content, "백링크"))
    if links:
        index = load_url_index()
        title_tokens = backlink_tokenize(title)
        weak = []
        for url in links:
            target = index.get(url.rstrip("/"))
            if target and relevance_score(tags, title_tokens, target["tags"], target["title"]) < BACKLINK_THRESHOLD:
                weak.append(target["title"])
        if weak:
            errors.append(f"관련성이 낮은 백링크 {len(weak)}건(태그·제목 키워드 겹침 없음): {weak[0][:50]}")

    tokens = topic_tokenize(title) | {tag.lower() for tag in tags}
    best_score, best_title, best_tags = 0.0, None, []
    for candidate in load_candidates():
        score = dice_score(tokens, candidate["tokens"])
        if score > best_score:
            best_score, best_title, best_tags = score, candidate["title"], candidate.get("tags", [])
    threshold = SERIES_THRESHOLD if shares_series_tag(tags, best_tags) else TOPIC_THRESHOLD
    if best_title and best_score >= threshold:
        errors.append(f"기존 발행 글과 주제가 겹칩니다(유사도 {best_score:.2f} >= {threshold:.2f}): {best_title[:50]}")
    return errors


def check_post(post) -> List[str]:
    errors: List[str] = []
    live_urls = [url for _item, url in reference_urls(reference_section_items(post.content)) if url]
    if live_urls and not any(urlparse(url).netloc in TRUSTED_REFERENCE_DOMAINS for url in live_urls):
        errors.append("참고문헌이 전부 비공식/블로그성 출처입니다. 공식 문서나 논문을 최소 1개 포함해야 합니다.")

    vague = [
        (claim.strip(), evidence.strip())
        for claim, _verdict, evidence in parse_fact_check_claims(post.content)
        if evidence.strip() and VAGUE_EVIDENCE_PATTERN.search(evidence) and not SPECIFIC_MARKER_PATTERN.search(evidence)
    ]
    if vague:
        errors.append(
            "근거가 모호한 표현(업계 리포트/교차 확인 등, 구체적 출처 표지 없음)으로만 채워진 claim이 "
            f"{len(vague)}건 있습니다: \"{vague[0][1][:60]}\" (wiki/Incident_Log.md#factcheck-2026-08-19-1 유사 사례 — 실제 원문/URL로 구체화할 것)"
        )
    errors.extend(quality_gate_errors(post))
    return errors


def check_run(run_id: str) -> Tuple[bool, List[str], List[str]]:
    context = load_validation_input(run_id)
    errors = check_post(context.post)
    return not errors, errors, []
