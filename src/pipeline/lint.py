import re
from typing import List, Tuple

import requests
from pydantic import ValidationError

from src.core.types import ArticleFrontmatter
from src.pipeline.validation_common import (
    internal_link_count,
    load_validation_input,
    parse_fact_check_claims,
    reference_section_items,
    reference_urls,
    section_exists,
    section_text,
    word_count,
)


def check_link_liveness(url: str, timeout: int = 5) -> Tuple[bool, str]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ai-blogging-linkcheck/1.0)"}
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        if response.status_code >= 400:
            response = requests.get(url, timeout=timeout, stream=True, headers=headers)
        return response.status_code < 400, f"HTTP {response.status_code}"
    except requests.RequestException as error:
        return False, str(error)


def lint_post(post, gate, skip_link_check: bool = False) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        ArticleFrontmatter.model_validate(post.metadata)
    except ValidationError as error:
        errors.append(f"frontmatter validation error: {error}")

    for section in gate.requiredSections:
        if not section_exists(post.content, section):
            errors.append(f"필수 섹션이 없습니다: {section}")

    items = reference_section_items(post.content)
    if len(items) < gate.minimumReferences:
        errors.append(f"참고문헌은 최소 {gate.minimumReferences}개가 필요합니다. 현재 {len(items)}개입니다.")
    if not skip_link_check:
        for item, url in reference_urls(items):
            if url is None:
                message = f"참고문헌에 URL이 없습니다: {item[:60]}"
                (errors if not gate.allowBrokenLinks else warnings).append(message)
                continue
            ok, detail = check_link_liveness(url)
            if not ok:
                message = f"참고문헌 링크가 접속되지 않습니다 ({detail}): {url}"
                (errors if not gate.allowBrokenLinks else warnings).append(message)

    for section, minimum in gate.sectionMinWords.items():
        actual = word_count(section_text(post.content, section))
        if actual < minimum:
            errors.append(f"'{section}' 섹션 분량이 부족합니다. 최소 {minimum}단어 필요, 현재 약 {actual}단어입니다.")

    if len(re.findall(r"```", post.content)) // 2 == 0 and not re.search(r"!\[[^\]]*\]\([^)]+\)", post.content):
        errors.append("코드 예시와 이미지가 모두 없습니다. 최소 1개는 포함해야 합니다.")

    link_text = "\n".join(section_text(post.content, name) for name in ("본문", "백링크", "종합적 의견"))
    link_count = internal_link_count(link_text)
    if link_count < gate.minimumInternalLinks:
        errors.append(f"자사 블로그 내부링크가 {link_count}개뿐입니다(최소 {gate.minimumInternalLinks}개 필요). 관련 발행 글을 '## 백링크' 또는 본문에 실제 라이브 URL로 링크해야 합니다.")

    if gate.requireOpinionDisclaimer:
        pattern = re.compile(r"^>.*(의견|견해|해석|사견)", re.MULTILINE)
        for section in ("작성자의 견해", "종합적 의견"):
            if not pattern.search(section_text(post.content, section)):
                errors.append(f"'{section}' 섹션에 의견/해석임을 밝히는 인용구(`>`) 안내문이 없습니다.")
    if "�" in post.content:
        errors.append("본문에 깨진 문자(U+FFFD)가 포함되어 있습니다. 인코딩을 확인하세요.")

    claims = parse_fact_check_claims(post.content)
    verdicts = [verdict.lower() for _claim, verdict, _evidence in claims]
    if "unverified" in verdicts:
        errors.append("미검증(unverified) 판정의 주장이 남아 있습니다.")
    if "contradicted" in verdicts:
        errors.append("반박된(contradicted) 판정의 주장이 남아 있습니다.")
    unsupported = [claim.strip() for claim, _verdict, evidence in claims if not evidence.strip()]
    if unsupported:
        errors.append(f"근거(출처) 없이 판정된 claim이 {len(unsupported)}건 있습니다: {unsupported[0][:60]}")
    return errors, warnings


def lint_run(run_id: str, skip_link_check: bool = False) -> Tuple[bool, List[str], List[str]]:
    context = load_validation_input(run_id)
    errors, warnings = lint_post(context.post, context.gate, skip_link_check)
    return not errors, errors, warnings
