"""
토픽 중복 검사 + 자동 대안 제시 — element_matrix의 '토픽' check(automated: false)를 채우는
작성 보조 도구. topic_selection 단계에서 주제를 확정하기 전에 실행한다.

배경: 지금까지는 wiki/Post_Topic_Backlog.md 발행완료 표를 육안 대조하는 것이 유일한 방법이었다
(element_matrix.토픽.check, wiki/rules/blog_article_pipeline_schema.md). 2026-08-23 사용자 요청으로
"경고만 하지 말고, 임계값을 넘으면 임계값 아래로 내려가는 대안 주제를 자동으로 제시"하도록 만들었다.
대안은 wiki/Blog_Writing_Rules.md 14번 수칙(차별화 필수)이 예시로 든 각도들
(실측 벤치마크/프로덕션 장애/흔치 않은 조합/비교표/예상 밖 동작/버전 한정)을 원래 주제에 결합해
생성하고, 각 대안을 다시 점수 매겨 실제로 임계값 아래로 내려간 것만 보여준다 — 무조건 통과되는
문구를 지어내는 게 아니라, 대안도 다시 같은 잣대로 재검증한다.

점수 방식: 오프라인 키워드 겹침(Dice 계수) — 임베딩/외부 API 없음. 완전히 다른 표현으로 같은 개념을
다루는 경우까지는 못 잡지만, 명백한 주제 중복(예: RDBMS 소개 글을 두 번 쓰는 것)은 확실히 잡는다.

사용법:
  python src/tools/check_topic_duplication.py --topic "주제 문장" [--tags "Advanced,Kafka"] [--threshold 0.35]

출력: 가장 유사한 기존 글 상위 5개 + 유사도 점수. 임계값 이상이면 대안 주제 후보(재검증 통과분만)를 함께 출력.
"""

import argparse
import glob
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import frontmatter
from src.core.paths import all_post_paths

DEFAULT_THRESHOLD = 0.35

# 시리즈(예: GoF 14부작, NoSQL/RDBMS #1·#2)는 같은 시리즈 태그를 공유하는 글끼리 제목/태그
# 유사도가 구조적으로 높게 나온다(2026-08-23, audit_published_posts.py 소급 감사에서 확인 —
# GoF 글끼리 0.81~0.87, NoSQL #1/#2 0.44 등, 전부 오탐이었음). Basics/Advanced/ETC 같은
# 카테고리·레벨 태그는 거의 모든 글이 공유하므로 시리즈 신호가 아니다 — 그걸 뺀 나머지 태그를
# 공유하면 시리즈로 보고 임계값을 크게 완화한다.
GENERIC_TAGS = {"basics", "advanced", "etc", "기초"}
SERIES_THRESHOLD = 0.9

STOPWORDS = {
    "the", "and", "for", "vs", "with", "of", "in", "on", "to", "a", "an", "is", "are",
    "이", "그", "저", "것", "수", "등", "및", "를", "을", "은", "는", "이란", "란", "위한",
}

# wiki/Blog_Writing_Rules.md 14번 수칙이 예시로 든 차별화 각도 — 원래 주제와 결합해 대안을 만든다.
DIFFERENTIATION_LEVERS = [
    "실제 벤치마크 수치로 보는",
    "실전 프로덕션 장애 사례 중심의",
    "흔치 않은 조합/트레이드오프로 본",
    "실측 비교표 기반",
    "직접 실행해보고 확인한 예상 밖 동작 중심의",
    "특정 최신 버전/스펙 기준",
]


def tokenize(text):
    words = re.split(r"[\s/():,\-\[\]\.]+", text.lower())
    return {w for w in words if len(w) > 1 and w not in STOPWORDS}


def load_candidates():
    candidates = []
    for path in all_post_paths():
        post = frontmatter.load(path)
        meta = post.metadata
        if meta.get("status") != "published":
            continue
        title = meta.get("title", "")
        tags = [t for t in meta.get("tags", []) if isinstance(t, str)]
        candidates.append({
            "title": title,
            "url": meta.get("url", ""),
            "tags": tags,
            "tokens": tokenize(title) | {t.lower() for t in tags},
        })
    return candidates


def shares_series_tag(tags_a, tags_b):
    """두 태그 집합이 같은 시리즈에 속하는지 판단한다. `{이름}_Series` 명시 태그(2026-08-23,
    wiki/Blog_Writing_Rules.md 17/18번 수칙, src/tools/manage_series_tags.py)가 있으면 그것을
    최우선 신호로 쓴다 — 정확히 같은 시리즈 태그를 공유해야만 True. 없으면(예: 아직 시리즈
    태그를 못 붙인 구버전 글) GENERIC_TAGS를 제외한 비일반 태그 겹침으로 폴백한다."""
    a_series = {t.lower() for t in tags_a if t.lower().endswith("_series")}
    b_series = {t.lower() for t in tags_b if t.lower().endswith("_series")}
    if a_series and b_series:
        return bool(a_series & b_series)

    a = {t.lower() for t in tags_a} - GENERIC_TAGS
    b = {t.lower() for t in tags_b} - GENERIC_TAGS
    return bool(a & b)


def dice_score(tokens_a, tokens_b):
    if not tokens_a or not tokens_b:
        return 0.0
    shared = len(tokens_a & tokens_b)
    return 2 * shared / (len(tokens_a) + len(tokens_b))


def score_topic(topic, tags, candidates):
    topic_tokens = tokenize(topic) | {t.lower() for t in (tags or [])}
    scored = [(dice_score(topic_tokens, c["tokens"]), c) for c in candidates]
    scored.sort(key=lambda x: -x[0])
    return topic_tokens, scored


def generate_alternatives(topic, tags, candidates, threshold):
    alternatives = []
    for lever in DIFFERENTIATION_LEVERS:
        variant = f"{lever} {topic}"
        _tokens, scored = score_topic(variant, tags, candidates)
        top_score = scored[0][0] if scored else 0.0
        if top_score < threshold:
            alternatives.append((variant, top_score))
    alternatives.sort(key=lambda x: x[1])
    return alternatives


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="검사할 주제 문장")
    parser.add_argument("--tags", default="", help="쉼표 구분 예상 태그(선택)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    candidates = load_candidates()
    if not candidates:
        print("발행된 글이 없어 비교 대상이 없습니다 — 신규 카테고리의 첫 글이면 정상.")
        return

    topic_tokens, scored = score_topic(args.topic, tags, candidates)
    top = scored[:5]

    print(f"주제: \"{args.topic}\"")
    print(f"가장 유사한 기존 글 상위 {len(top)}개:")
    for score, c in top:
        flag = " ⚠️" if score >= args.threshold else ""
        print(f"  [{score:.2f}]{flag} {c['title']}")
        if c["url"]:
            print(f"         {c['url']}")

    max_score = top[0][0] if top else 0.0
    effective_threshold = args.threshold
    if top and shares_series_tag(tags, top[0][1].get("tags", [])):
        effective_threshold = max(args.threshold, SERIES_THRESHOLD)
        print(f"\n(참고: 최상위 후보와 시리즈 태그를 공유해 임계값을 {effective_threshold:.2f}로 완화 적용)")

    if max_score >= effective_threshold:
        print(f"\n⚠️ 임계값({effective_threshold:.2f}) 이상 — 겹치는 주제로 판단됩니다.")
        print(f"겹치는 키워드: {sorted(topic_tokens & top[0][1]['tokens'])}")
        print("\n임계값 아래로 재검증된 대안 주제:")
        alts = generate_alternatives(args.topic, tags, candidates, effective_threshold)
        if not alts:
            print("  (자동 생성한 대안도 전부 임계값을 못 넘김 — 직접 다른 각도를 찾아야 합니다.)")
        else:
            for variant, score in alts:
                print(f"  [{score:.2f}] {variant}")
    else:
        print(f"\n✅ 임계값({effective_threshold:.2f}) 미만 — 채택 가능한 주제입니다.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
