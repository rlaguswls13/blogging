"""
의견/차별화 통찰력 검사 — element_matrix의 '의견/차별화' check(automated: false)를 채우는 작성
보조 도구. "통찰이 있는가"는 여전히 코드로 판단 못 하지만, 2026-08-23 사용자 요청으로 단일 점수
하나가 아니라 **서로 다른 실패 유형을 구분**해서 보여주도록 5개 하위 지표로 나눴다 — 뭉뚱그린
점수 하나보다, "어떤 문제인지"가 바로 보이는 게 실제로 고칠 때 더 쓸모 있다.

대상 섹션: '차별화 포인트', '작성자의 견해', '종합적 의견' (전부 통찰/의견이 핵심인 섹션).

5개 하위 지표:
  1. **구체성(specificity)**: 숫자/버전/날짜/코드·CLI 참조/URL 개수 — 적을수록 추상적.
  2. **상투구 비율(filler_ratio)**: "다양한 관점에서", "결론적으로" 같은 상투적 도입/마무리 문구가
     전체 문장에서 차지하는 비율(wiki/Incident_Log.md의 "47개 글 토씨 하나 안 틀린 문장 반복" 사고
     재발 방지).
  3. **타 글과의 문구 재사용(cross_post_similarity)**: 같은 섹션을 이미 발행된 다른 글들과
     bigram Jaccard로 비교 — 높으면 복붙/재탕 의심.
  4. **주장-근거 정합성(claim_evidence_alignment)**: '차별화 포인트'가 주장한 차별화 유형(벤치마크/
     프로덕션 이슈/비교표/직접 실행/예상 밖 동작)이 실제로 본문에 그 유형에 맞는 증거(숫자+단위,
     에러명, 마크다운 표, 코드펜스, 대조 표현)로 뒷받침되는지 교차 확인.
  5. **어휘 다양성(type_token_ratio)**: 고유 단어 수 / 전체 단어 수 — 너무 낮으면 같은 말 반복(패딩).

사용법:
  python src/tools/check_opinion_insight.py --run <run_id>
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import frontmatter
from src.core.paths import all_post_paths, run_directory

TARGET_SECTIONS = ["차별화 포인트", "작성자의 견해", "종합적 의견"]

FILLER_PHRASES = [
    "다양한 관점에서", "종합적으로 고려하면", "결론적으로", "요약하자면", "말할 것도 없이",
    "누구나 알다시피", "여러 가지 측면에서", "다각도로", "전반적으로 볼 때", "일반적으로 말해서",
]

SPECIFICITY_PATTERN = re.compile(
    r"\d+(\.\d+)?\s*(ms|초|분|배|%|MB|GB|KB|req/s|바이트|자|줄|개|버전)"
    r"|https?://|RFC\s*\d+|v\d+\.\d+|[A-Z][a-zA-Z]+\.[a-zA-Z]{2,}"
    r"|[A-Za-z]{2,}\d{2,}"  # 기술 식별자(예: X25519MLKEM768, TLS13, HTTP2)
    r"|\b\d+(\.\d+)?\b"  # 단위 없는 순수 숫자도 약한 구체성 신호로 포함
)

CLAIM_TYPES = {
    "벤치마크": re.compile(r"\d+(\.\d+)?\s*(ms|초|배|%|req/s)"),
    "실측": re.compile(r"\d+(\.\d+)?\s*(ms|초|배|%|req/s)"),
    "프로덕션": re.compile(r"[A-Z][a-zA-Z]*(Exception|Error|Timeout|Fault)|장애|에러|오류"),
    "장애": re.compile(r"[A-Z][a-zA-Z]*(Exception|Error|Timeout|Fault)|장애|에러|오류"),
    "비교표": re.compile(r"^\s*\|.+\|.+\|\s*$", re.MULTILINE),
    "직접 실행": re.compile(r"```"),
    "직접 캡처": re.compile(r"```"),
    "직접 돌려본": re.compile(r"```"),
    "예상 밖": re.compile(r"예상|의외|놀랍게도|하지만|그런데|반대로|달랐다"),
}


def extract_section(body, heading):
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##(?!#)|\Z)", re.MULTILINE | re.DOTALL)
    m = pattern.search(body)
    return m.group(1).strip() if m else ""


def split_sentences(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    return [s.strip() for s in re.split(r"(?<=[.!?다요])\s+|\n+", text) if s.strip()]


def bigrams(text):
    words = re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
    return set(zip(words, words[1:])) if len(words) > 1 else set()


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def check_specificity(text):
    hits = SPECIFICITY_PATTERN.findall(text)
    return len(hits)


def check_filler_ratio(text):
    sentences = split_sentences(text)
    if not sentences:
        return 0.0, []
    filler_hits = [s for s in sentences if any(p in s for p in FILLER_PHRASES)]
    return len(filler_hits) / len(sentences), filler_hits


def check_type_token_ratio(text):
    words = re.findall(r"[가-힣A-Za-z0-9]+", text)
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def check_cross_post_similarity(text, section_name, own_slug, corpus_index):
    my_bigrams = bigrams(text)
    best = (0.0, None)
    for slug, sections in corpus_index.items():
        if slug == own_slug:
            continue
        other_text = sections.get(section_name, "")
        if not other_text:
            continue
        score = jaccard(my_bigrams, bigrams(other_text))
        if score > best[0]:
            best = (score, slug)
    return best


def check_claim_evidence_alignment(differentiation_text, body_text):
    claimed_types = [k for k in CLAIM_TYPES if k in differentiation_text]
    results = []
    for claim_type in claimed_types:
        pattern = CLAIM_TYPES[claim_type]
        supported = bool(pattern.search(body_text))
        results.append((claim_type, supported))
    return results


def build_corpus_index():
    index = {}
    for path in all_post_paths():
        post = frontmatter.load(path)
        slug = post.metadata.get("slug") or path.stem
        sections = {name: extract_section(post.content, name) for name in TARGET_SECTIONS}
        index[slug] = sections
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True)
    parser.add_argument("--similarity-threshold", type=float, default=0.35)
    args = parser.parse_args()

    final_path = run_directory(args.run) / "final.md"
    if not final_path.exists():
        print(f"오류: {final_path} 없음", file=sys.stderr)
        sys.exit(1)

    post = frontmatter.load(final_path)
    slug = post.metadata.get("slug") or args.run
    body_text = post.content

    print("의견/차별화 통찰력 점검 (5개 하위 지표, 단일 점수 아님)\n")
    corpus_index = build_corpus_index()

    for section_name in TARGET_SECTIONS:
        text = extract_section(body_text, section_name)
        if not text:
            print(f"[{section_name}] 섹션 없음 — 건너뜀\n")
            continue

        print(f"## {section_name}")

        specificity = check_specificity(text)
        print(f"  1. 구체성: 숫자/URL/버전/도메인 등 구체 지표 {specificity}개"
              f"{'  ⚠️ 너무 적음(추상적 서술 위주일 수 있음)' if specificity == 0 else ''}")

        filler_ratio, filler_hits = check_filler_ratio(text)
        flag = "  ⚠️ 상투구 비율 높음" if filler_ratio > 0.2 else ""
        print(f"  2. 상투구 비율: {filler_ratio:.0%}{flag}")
        if filler_hits:
            print(f"     예: \"{filler_hits[0][:50]}\"")

        sim_score, sim_slug = check_cross_post_similarity(text, section_name, slug, corpus_index)
        flag = "  ⚠️ 다른 글과 문구 재사용 의심" if sim_score >= args.similarity_threshold else ""
        print(f"  3. 타 글과의 유사도: {sim_score:.0%}"
              f"{f' (가장 유사: {sim_slug})' if sim_slug else ''}{flag}")

        ttr = check_type_token_ratio(text)
        flag = "  ⚠️ 어휘 다양성 낮음(같은 말 반복 의심)" if ttr < 0.4 else ""
        print(f"  5. 어휘 다양성(TTR): {ttr:.0%}{flag}")
        print()

    diff_text = extract_section(body_text, "차별화 포인트")
    if diff_text:
        print("## 4. 주장-근거 정합성 (차별화 포인트가 주장한 유형이 본문에서 실제로 뒷받침되는지)")
        alignment = check_claim_evidence_alignment(diff_text, body_text)
        if not alignment:
            print("  차별화 포인트에서 알려진 차별화 유형 키워드를 못 찾음(자유 서술 — 판단 보류)")
        else:
            for claim_type, supported in alignment:
                mark = "✅" if supported else "⚠️ 본문에서 뒷받침 증거를 못 찾음"
                print(f"  \"{claim_type}\" 주장 — {mark}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
