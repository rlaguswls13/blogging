"""
시리즈(예: GoF 14부작, NoSQL/RDBMS #1·#2) 소속 글에 검색·분류용 커스텀 태그
`{키워드}_Series`(예: `GoF_Series`, `NoSQL_Series`)를 붙이는 도구.

배경: check_topic_duplication.py/audit_published_posts.py는 "같은 시리즈면 태그·제목
유사도가 구조적으로 높다"는 사실을 이용해 임계값을 완화하지만(shares_series_tag,
GENERIC_TAGS 제외 태그 겹침), 그건 "오탐 억제"용 휴리스틱일 뿐 "이 글들이 한 시리즈다"라는
사실 자체를 사람이 나중에 검색·필터링할 수 있는 형태로 저장해두지는 않는다(2026-08-23
사용자 요청). 이 도구는 그 시리즈 소속 정보를 명시적 태그로 못박는다.

시리즈 판별 방법(정밀도 우선, 오검출 방지):
  1. **주 신호 — 제목의 대괄호 접두사**: "[GoF 디자인 패턴] 1. ..." / "[NoSQL 깊이 읽기 #1] ..."
     처럼 제목이 "[시리즈명 #N]" 또는 "[시리즈명] N." 패턴을 따르는 글들을 접두사(번호 제외)로
     묶는다 — 작성 시점에 사람/파이프라인이 이미 "이건 한 시리즈다"라고 표시해둔 것이므로 가장
     신뢰도 높은 신호.
  2. **보조 신호 — 태그 공유 + 제목 유사도**: 대괄호 패턴에 안 걸리는 시리즈 인덱스/가이드 글
     (예: "GoF 핵심 14가지... 인덱스 가이드")도 있을 수 있다. 이런 글은, 1번에서 찾은 클러스터
     멤버 전원이 공유하는 비일반 태그(GENERIC_TAGS 제외)를 그대로 갖고 있으면서 동시에 클러스터
     내 최소 1개 글과의 제목 Dice 유사도가 0.35 이상일 때만 같은 시리즈로 편입한다 — 태그만
     같고 제목이 안 겹치면(예: 'SQL vs NoSQL' 총론 글이 'NoSQL' 태그를 우연히 공유하는 경우)
     편입하지 않는다. 이 이중 조건 덕분에 NoSQL 시리즈(진짜 멤버 2개)에 무관한 글이 잘못
     끼어들지 않으면서도 GoF 시리즈에는 인덱스 가이드 글이 정확히 편입된다(2026-08-23 검증됨).

사용법:
  python src/tools/manage_series_tags.py --scan
      감지된 시리즈 클러스터와 부여될 태그를 보여주기만 한다(변경 없음).

  python src/tools/manage_series_tags.py --apply --dry-run
      실제로 적용했을 때 어떤 파일에 어떤 태그가 추가되는지만 보여준다(변경 없음).

  python src/tools/manage_series_tags.py --apply
      로컬 frontmatter tags에 시리즈 태그를 추가하고, frontmatter.id가 있는 글은 라이브
      Blogger 게시물의 labels도 함께 갱신한다(본문 HTML은 건드리지 않음 — 태그/라벨만 patch).
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import frontmatter
from dotenv import load_dotenv

from src.core.paths import all_post_paths
from src.tools.check_topic_duplication import tokenize, dice_score, GENERIC_TAGS

load_dotenv()

BRACKET_PREFIX_RE = re.compile(r"^\[(.+?)\]")
SIMILARITY_THRESHOLD = 0.35


def _series_keyword(prefix):
    """'GoF 디자인 패턴' -> 'GoF', 'NoSQL 깊이 읽기' -> 'NoSQL' — 접두사의 첫 단어를 시리즈
    키워드로 쓴다(대개 그 시리즈를 대표하는 고유명사가 맨 앞에 온다)."""
    return prefix.split()[0]


def load_posts():
    posts = []
    for path in all_post_paths():
        post = frontmatter.load(path)
        if post.metadata.get("status") != "published":
            continue
        title = post.metadata.get("title", "")
        tags = [t for t in post.metadata.get("tags", []) if isinstance(t, str)]
        posts.append({
            "path": path,
            "meta": post.metadata,
            "title": title,
            "tags": tags,
            "tokens": tokenize(title) | {t.lower() for t in tags},
        })
    return posts


def detect_series(posts):
    """{series_tag: [post, ...]} 반환."""
    bracket_clusters = {}
    for post in posts:
        m = BRACKET_PREFIX_RE.match(post["title"])
        if not m:
            continue
        prefix = re.sub(r"\s*#\d+\s*$", "", m.group(1)).strip()
        bracket_clusters.setdefault(prefix, []).append(post)

    clusters = {}
    for prefix, members in bracket_clusters.items():
        if len(members) < 2:
            continue
        common_tags = set(members[0]["tags"])
        for m in members[1:]:
            common_tags &= set(m["tags"])
        common_tags = {t for t in common_tags if t.lower() not in GENERIC_TAGS}
        clusters[prefix] = (members, common_tags)

    # 같은 태그가 서로 다른(진짜 별개인) 시리즈의 공통 태그로도 쓰이면(예: 'Database'가 NoSQL
    # 시리즈와 RDBMS 시리즈 양쪽 모두의 공통 태그) 그 태그로는 시리즈 밖 글을 끌어들이지 않는다
    # — 두 시리즈가 제목에 같은 접두어 패턴("... 깊이 읽기")을 써서 제목 유사도까지 우연히
    # 겹치는 경우, 태그 하나만으로는 오검출을 못 막기 때문(2026-08-23, 실제로 발견된 문제).
    tag_to_clusters = {}
    for prefix, (_members, common_tags) in clusters.items():
        for t in common_tags:
            tag_to_clusters.setdefault(t, set()).add(prefix)
    exclusive_tags_by_cluster = {
        prefix: {t for t in common_tags if len(tag_to_clusters[t]) == 1}
        for prefix, (_members, common_tags) in clusters.items()
    }

    series = {}
    for prefix, (members, _common_tags) in clusters.items():
        series_tag = f"{_series_keyword(prefix)}_Series"
        anchor_tags = exclusive_tags_by_cluster[prefix]

        cluster_paths = {m["path"] for m in members}
        extra = []
        if anchor_tags:
            for post in posts:
                if post["path"] in cluster_paths:
                    continue
                if not (set(post["tags"]) & anchor_tags):
                    continue
                best = max((dice_score(post["tokens"], m["tokens"]) for m in members), default=0.0)
                if best >= SIMILARITY_THRESHOLD:
                    extra.append(post)

        series[series_tag] = members + extra
    return series


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", action="store_true")
    group.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    posts = load_posts()
    series = detect_series(posts)

    if not series:
        print("감지된 시리즈가 없습니다.")
        return

    to_apply = {}
    for series_tag, members in series.items():
        needs_tag = [m for m in members if series_tag not in m["tags"]]
        print(f"\n=== {series_tag} ({len(members)}개, 태그 필요 {len(needs_tag)}개) ===")
        for m in members:
            has = "이미 있음" if series_tag in m["tags"] else "추가 필요"
            print(f"  [{has}] {m['path'].relative_to(m['path'].parent.parent)} — {m['title'][:50]}")
        if needs_tag:
            to_apply[series_tag] = needs_tag

    if args.scan or not to_apply:
        return

    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    service = None
    if not args.dry_run:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        credentials = Credentials(
            token=None,
            refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["BLOGGER_CLIENT_ID"],
            client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
        )
        service = build("blogger", "v3", credentials=credentials)

    print()
    for series_tag, members in to_apply.items():
        for post in members:
            path = post["path"]
            tag = "[DRY-RUN]" if args.dry_run else "[APPLY]"
            print(f"{tag} {path.name}: + {series_tag}")

            new_tags = post["tags"] + [series_tag]
            if args.dry_run:
                continue

            full = frontmatter.load(path)
            full.metadata["tags"] = new_tags
            path.write_text(frontmatter.dumps(full), encoding="utf-8")

            post_id = post["meta"].get("id")
            if not post_id:
                print(f"       [경고] frontmatter에 id 없음 - 라이브 라벨 갱신 생략")
                continue
            service.posts().patch(
                blogId=blog_id, postId=post_id, body={"labels": new_tags},
            ).execute()
            print(f"       라이브 게시물 {post_id} 라벨 갱신 완료")

    verb = "시뮬레이션" if args.dry_run else "완료"
    total = sum(len(v) for v in to_apply.values())
    print(f"\n총 {total}건 태그 부여 {verb}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
