"""
발행된 글 전체(content/posts/**/*.md)에 새로 만든 5개 check-quality 도구(2026-08-23 신설)를
소급 적용하는 읽기 전용 감사 도구. 라이브/로컬 어느 것도 수정하지 않는다 — 문제를 찾아서
보고만 한다, 실제 수정은 이 결과를 보고 별도로 진행한다.

대상: 사실검증 근거 모호성(vague_evidence), 코드 구문/설명-일치, 백링크 관련성, 의견/차별화
5개 하위 지표, 토픽 중복(자기 자신 제외). 전부 근사 신호이며 draft 단계 도구를 그대로 재사용한다
(src/tools/check_*.py에 2026-08-23 추가한 --file 옵션으로 발행된 파일도 검사 가능해짐).

사용법:
  python src/tools/audit_published_posts.py [--limit N] [--only-issues]
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import frontmatter
from src.core.paths import all_post_paths
from src.pipeline.validate import (
    section_text, parse_fact_check_claims, VAGUE_EVIDENCE_PATTERN, SPECIFIC_MARKER_PATTERN,
)
from src.tools.check_code_blocks import extract_code_blocks, SYNTAX_CHECKERS, check_logic_match
from src.tools.check_backlink_relevance import (
    relevance_score, load_url_index, extract_section as backlink_extract_section,
    DEFAULT_THRESHOLD as BACKLINK_THRESHOLD,
)
from src.tools.check_opinion_insight import (
    extract_section as opinion_extract_section, check_specificity, check_filler_ratio,
    check_type_token_ratio, check_cross_post_similarity, check_claim_evidence_alignment,
    build_corpus_index, TARGET_SECTIONS, RELAXED_SPECIFICITY_SECTIONS,
)
from src.tools.check_topic_duplication import (
    tokenize as topic_tokenize, dice_score, load_candidates, shares_series_tag, SERIES_THRESHOLD,
)


def audit_vague_evidence(body):
    claim_rows = parse_fact_check_claims(body)
    return [
        (claim.strip(), evidence.strip())
        for claim, verdict, evidence in claim_rows
        if evidence.strip() and VAGUE_EVIDENCE_PATTERN.search(evidence) and not SPECIFIC_MARKER_PATTERN.search(evidence)
    ]


def audit_code_blocks(body):
    issues = []
    for lang, code, context in extract_code_blocks(body):
        checker = SYNTAX_CHECKERS.get(lang.lower())
        if checker:
            err = checker(code)
            if err:
                issues.append(f"구문 오류({lang}): {err}")
        _claimed, missing = check_logic_match(code, context)
        if missing:
            issues.append(f"설명-코드 불일치({lang}): {missing}")
    return issues


def audit_backlinks(body, tags, title, url_index):
    section = backlink_extract_section(body, "백링크")
    links = re.findall(r"\[([^\]]*)\]\((https?://[^)]+)\)", section)
    title_tokens = re.findall(r"[가-힣A-Za-z0-9]+", title.lower())
    issues = []
    for label, url in links:
        target = url_index.get(url.rstrip("/"))
        if not target:
            issues.append(f"대상 미확인: {label}")
            continue
        score = relevance_score(tags, title_tokens, target["tags"], target["title"])
        if score < BACKLINK_THRESHOLD:
            issues.append(f"관련성 낮음({score}): {label}")
    return issues


def audit_opinion(body, slug, corpus_index, similarity_threshold=0.35):
    issues = []
    for section_name in TARGET_SECTIONS:
        text = opinion_extract_section(body, section_name)
        if not text:
            continue
        if check_specificity(text) == 0 and section_name not in RELAXED_SPECIFICITY_SECTIONS:
            issues.append(f"[{section_name}] 구체성 0 (숫자/URL/기술식별자 없음)")
        filler_ratio, _hits = check_filler_ratio(text)
        if filler_ratio > 0.2:
            issues.append(f"[{section_name}] 상투구 비율 {filler_ratio:.0%}")
        sim_score, sim_slug = check_cross_post_similarity(text, section_name, slug, corpus_index)
        if sim_score >= similarity_threshold:
            issues.append(f"[{section_name}] 타 글({sim_slug})과 유사도 {sim_score:.0%}")
        ttr = check_type_token_ratio(text)
        if ttr < 0.4:
            issues.append(f"[{section_name}] 어휘 다양성(TTR) {ttr:.0%}")

    diff_text = opinion_extract_section(body, "차별화 포인트")
    if diff_text:
        for claim_type, supported in check_claim_evidence_alignment(diff_text, body):
            if not supported:
                issues.append(f"[차별화 포인트] \"{claim_type}\" 주장이 본문에서 뒷받침 안 됨")
    return issues


def audit_topic_duplication(title, tags, own_slug, candidates, threshold=0.35):
    topic_tokens = topic_tokenize(title) | {t.lower() for t in tags}
    best = (0.0, None, [])
    for c in candidates:
        if c.get("slug") == own_slug:
            continue
        score = dice_score(topic_tokens, c["tokens"])
        if score > best[0]:
            best = (score, c["title"], c.get("tags", []))
    score, best_title, best_tags = best
    effective_threshold = SERIES_THRESHOLD if shares_series_tag(tags, best_tags) else threshold
    if score >= effective_threshold:
        return [f"기존 글과 유사도 {score:.2f}: {best_title}"]
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only-issues", action="store_true", help="문제 없는 글은 출력 생략")
    args = parser.parse_args()

    paths = all_post_paths()
    if args.limit:
        paths = paths[: args.limit]

    print(f"감사 대상: {len(paths)}개 발행 글\n")

    url_index = load_url_index()
    corpus_index = build_corpus_index()

    # topic_duplication용 candidates는 load_candidates()가 slug를 안 담으므로 직접 구성
    topic_candidates = []
    for path in all_post_paths():
        post = frontmatter.load(path)
        meta = post.metadata
        if meta.get("status") != "published":
            continue
        title = meta.get("title", "")
        tags = [t for t in meta.get("tags", []) if isinstance(t, str)]
        topic_candidates.append({
            "slug": meta.get("slug") or path.stem,
            "title": title,
            "tags": tags,
            "tokens": topic_tokenize(title) | {t.lower() for t in tags},
        })

    total_issues = 0
    posts_with_issues = 0

    for path in paths:
        post = frontmatter.load(path)
        meta = post.metadata
        slug = meta.get("slug") or path.stem
        title = meta.get("title", "")
        tags = [t for t in meta.get("tags", []) if isinstance(t, str)]
        body = post.content

        findings = {
            "사실검증(모호한 근거)": [f"\"{ev[:50]}\"" for _c, ev in audit_vague_evidence(body)],
            "코드": audit_code_blocks(body),
            "백링크": audit_backlinks(body, tags, title, url_index),
            "의견/차별화": audit_opinion(body, slug, corpus_index),
            "토픽 중복": audit_topic_duplication(title, tags, slug, topic_candidates),
        }

        issue_count = sum(len(v) for v in findings.values())
        if issue_count == 0 and args.only_issues:
            continue

        total_issues += issue_count
        if issue_count > 0:
            posts_with_issues += 1

        rel_path = path.relative_to(path.parent.parent)
        status = "✅" if issue_count == 0 else f"⚠️ {issue_count}건"
        print(f"[{status}] {rel_path} — {title[:60]}")
        for category, items in findings.items():
            for item in items:
                print(f"    · {category}: {item}")

    print(f"\n총 {len(paths)}개 중 {posts_with_issues}개 글에서 문제 {total_issues}건 발견.")
    print("이 결과는 근사 신호입니다 — 실제 수정 전에 각 항목을 사람이 다시 확인할 것.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
