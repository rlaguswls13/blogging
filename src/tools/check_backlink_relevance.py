"""
백링크 관련성 검증 — element_matrix의 '백링크' check(automated: false)를 채우는 작성 보조 도구.

배경: 기존 게이트(internal_link_count)는 자사 블로그 링크 개수만 세고, 그 링크가 이 글과 실제로
관련 있는지는 전혀 보지 않는다(element_matrix.백링크.check 참고). suggest_internal_links.py는
"추천"만 하고, 이미 draft에 적어놓은 백링크가 실제로 관련 있는지 "검증"하는 도구는 없었다.
이 도구는 suggest_internal_links.py와 같은 태그/키워드 겹침 스코어링을 거꾸로 적용한다 — 이미 쓴
'## 백링크' 각 링크의 대상 글이 이 글과 태그를 얼마나 공유하는지 점수를 매겨, 0점(완전 무관)에
가까운 링크를 경고한다.

사용법:
  python src/tools/check_backlink_relevance.py --run <run_id> [--threshold 0.1]

temp/runs/<run_id>/final.md를 읽어 frontmatter tags와 '## 백링크' 섹션의 링크를 파싱한다.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import frontmatter
from src.core.paths import all_post_paths, run_directory

DEFAULT_THRESHOLD = 1  # score < 1 (즉 태그 안 겹치고 제목 키워드도 안 겹침)이면 경고
STOPWORDS = {
    "the", "and", "for", "vs", "with", "of", "in", "on", "to", "a", "an", "is", "are",
    "이", "그", "저", "것", "수", "등", "및", "를", "을", "은", "는", "이란", "란", "위한",
}


def tokenize(text):
    words = re.split(r"[\s/():,\-\[\]\.]+", text.lower())
    return {w for w in words if len(w) > 1 and w not in STOPWORDS}


def relevance_score(my_tags, my_title_tokens, target_tags, target_title):
    """suggest_internal_links.py와 동일한 스코어링(태그 겹침*2 + 제목 키워드 히트) — 태그가
    가장 신뢰도 높은 신호이므로 순수 텍스트 유사도(Dice)보다 이걸 주 지표로 쓴다. 제목 전체를
    토큰화해 겹치는 걸 재는 방식은 긴 제목끼리 점수가 구조적으로 낮게 나와(짧은 공유 키워드가
    긴 제목 안에 묻힘) 실제로 관련 있는 글도 오탐 경고하는 문제가 있었다(2026-08-23 조정)."""
    tag_overlap = len(set(t.lower() for t in my_tags) & set(t.lower() for t in target_tags))
    title_lower = target_title.lower()
    keyword_hits = sum(1 for k in my_title_tokens if k in title_lower)
    return tag_overlap * 2 + keyword_hits


def load_url_index():
    index = {}
    for path in all_post_paths():
        post = frontmatter.load(path)
        meta = post.metadata
        if meta.get("status") != "published" or not meta.get("url"):
            continue
        title = meta.get("title", "")
        tags = [t for t in meta.get("tags", []) if isinstance(t, str)]
        index[meta["url"].rstrip("/")] = {"title": title, "tags": tags}
    return index


def extract_section(body, heading):
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##(?!#)|\Z)", re.MULTILINE | re.DOTALL)
    m = pattern.search(body)
    return m.group(1) if m else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", help="run_id (temp/runs/<run_id>/final.md) — draft 단계용")
    group.add_argument("--file", help="이미 발행된 content/posts/<Category>/<slug>.md 등 임의 경로 — 소급 감사용(2026-08-23 신설)")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    final_path = Path(args.file) if args.file else (run_directory(args.run) / "final.md")
    if not final_path.exists():
        print(f"오류: {final_path} 없음", file=sys.stderr)
        sys.exit(1)

    post = frontmatter.load(final_path)
    title = post.metadata.get("title", "")
    tags = [t for t in post.metadata.get("tags", []) if isinstance(t, str)]
    my_title_tokens = tokenize(title)

    backlink_section = extract_section(post.content, "백링크")
    links = re.findall(r"\[([^\]]*)\]\((https?://[^)]+)\)", backlink_section)
    if not links:
        print("'## 백링크'에서 링크를 찾지 못했습니다.")
        return

    url_index = load_url_index()
    print(f"이 글: \"{title}\" (tags: {tags})\n")
    print(f"백링크 {len(links)}개 관련성 점수:")

    weak = []
    for label, url in links:
        target = url_index.get(url.rstrip("/"))
        if not target:
            print(f"  [??] {label}  <- 대상 글을 카탈로그에서 못 찾음(URL 오타 또는 미발행 가능성)")
            continue
        score = relevance_score(tags, my_title_tokens, target["tags"], target["title"])
        flag = " ⚠️ 관련성 낮음" if score < args.threshold else ""
        print(f"  [{score}]{flag} {label}")
        if score < args.threshold:
            weak.append((label, url, score))

    if weak:
        print(f"\n⚠️ {len(weak)}개 링크가 관련성 임계값({args.threshold}) 미만입니다 — "
              f"태그 기준으로는 무관해 보입니다. 실제로 이 글과 관련 있는지 직접 확인하거나, "
              f"src/tools/suggest_internal_links.py로 더 관련 있는 후보를 찾아 교체하세요.")
    else:
        print("\n✅ 전부 관련성 임계값 이상입니다.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
