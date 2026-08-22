"""
초안 작성 중(validate 이전) 내부링크 후보를 추천하는 작성 보조 도구.

배경: validate.py의 internal_link_count 체크가 2026-08-22부터 warning에서 error로 승격됐다
(wiki/Blog_Writing_Rules.md 15번 수칙) — 이제 최소 2개를 못 채우면 발행 자체가 막힌다. 그런데
"어떤 기존 글이 관련 있는지"는 게이트가 대신 찾아주지 못하고 작성자가 직접 골라야 한다. 이 도구는
`content/posts/*.md`의 frontmatter(tags/title)만 읽어(본문은 안 읽음, 빠름) 태그·키워드 겹침으로
후보를 점수순 랭킹해 `## 백링크`에 바로 붙여넣을 마크다운 링크 형식으로 출력한다.

네트워크 호출 없음, 오프라인. 이미 발행된 글이 하나도 없거나 겹치는 게 없으면 빈 결과를 보고한다
(신규 카테고리의 첫 글이면 정상 — wiki/Blog_Writing_Rules.md 15번 수칙 참고).

사용법:
  python src/tools/suggest_internal_links.py --tags "Advanced,Spring" [--keywords "리액티브,비동기"] [--limit 5]
  python src/tools/suggest_internal_links.py --topic "Spring WebFlux 스레드 모델" [--limit 5]
      --topic을 주면 제목/태그 매칭용 키워드로 공백 분리해 자동 사용한다.
"""

import argparse
import glob
import sys
from pathlib import Path

import frontmatter

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
POSTS_GLOB = str(REPO_ROOT / "content" / "posts" / "*" / "*.md")  # Basics/Advanced/ETC 하위폴더


def load_candidates():
    candidates = []
    for path in sorted(glob.glob(POSTS_GLOB)):
        post = frontmatter.load(path)
        meta = post.metadata
        if meta.get("status") != "published" or not meta.get("url"):
            continue
        candidates.append({
            "title": meta.get("title", ""),
            "tags": [t for t in meta.get("tags", []) if isinstance(t, str)],
            "url": meta.get("url"),
        })
    return candidates


def score(candidate, tags, keywords):
    tag_overlap = len(set(t.lower() for t in candidate["tags"]) & set(t.lower() for t in tags))
    title_lower = candidate["title"].lower()
    keyword_hits = sum(1 for k in keywords if k.lower() in title_lower)
    return tag_overlap * 2 + keyword_hits


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tags", default="", help="쉼표 구분 태그 목록")
    parser.add_argument("--keywords", default="", help="쉼표 구분 키워드(제목 매칭용)")
    parser.add_argument("--topic", default="", help="주제 문장 — 공백 분리해 키워드로 사용")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if args.topic:
        keywords += [w for w in args.topic.split() if len(w) > 1]

    if not tags and not keywords:
        print("오류: --tags, --keywords, --topic 중 최소 하나는 지정해야 합니다.", file=sys.stderr)
        sys.exit(1)

    candidates = load_candidates()
    scored = [(score(c, tags, keywords), c) for c in candidates]
    scored = [(s, c) for s, c in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        print("관련 후보를 찾지 못했습니다 — 신규 카테고리의 첫 글이라면 정상입니다.")
        print("(minimumInternalLinks 게이트를 채울 수 없다면 wiki/Blog_Writing_Rules.md 15번 수칙 참고)")
        return

    print(f"내부링크 후보 {min(len(scored), args.limit)}개 (## 백링크에 붙여넣기):\n")
    for _score, c in scored[: args.limit]:
        print(f"- [{c['title']}]({c['url']})")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
