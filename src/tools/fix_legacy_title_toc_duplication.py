"""
2026-08-05 ~ 08-13 사이 발행된 구버전 글 본문에 남아있는 수동 "## {축약 제목}" 헤딩과
수동 "목차" 불릿 리스트를 제거하는 1회성 마이그레이션 도구.

배경: src/pipeline/converter.py는 (a) 본문 첫 H1을 <h2 class="post-body-title">로
재삽입하고, (b) '## 본문' 직전에 헤딩을 스캔해 자동 목차(<details class="toc-details">)를
삽입한다. 두 기능 모두 신규 파이프라인 도입 이후 추가된 것인데, 그보다 먼저 발행된 17개
글은 작성 당시 사람/구버전 파이프라인이 직접 써넣은 "## {축약 제목}"과 "목차\n- [1. ...]"
블록을 본문에 그대로 갖고 있다. 그 결과 컨버터가 자동 생성한 버전이 위에 하나 더 겹쳐져
라이브 페이지에 제목과 목차가 각각 두 번씩 렌더링된다(2026-08-23 사용자가 스크린샷으로 보고).

이 도구는 그 두 레거시 블록만 정확히 제거한다(그 외 본문 내용은 건드리지 않음) — 제거 후
컨버터가 만드는 자동 버전 하나만 남게 되어 중복이 사라진다.

사용법:
  python src/tools/fix_legacy_title_toc_duplication.py --scan
      영향받는 파일과 제거될 블록을 보여주기만 한다(변경 없음).

  python src/tools/fix_legacy_title_toc_duplication.py --apply --dry-run
      로컬 파일에 적용했을 때의 결과(diff)만 보여준다(파일/라이브 변경 없음).

  python src/tools/fix_legacy_title_toc_duplication.py --apply
      로컬 content/posts/<Category>/<slug>.md를 실제로 고치고,
      frontmatter.id가 있는 글은 convert_markdown_to_html()로 재생성한 HTML을
      라이브 Blogger 게시물에도 반영한다.
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
from src.pipeline.converter import convert_markdown_to_html

load_dotenv()

# H1 바로 다음에 오는, H1 제목을 그대로(혹은 그 축약형으로) 담고 있는 "## ..." 한 줄
# (구버전이 직접 써넣은 축약 제목) — 컨버터가 H1 자체를 <h2 class="post-body-title">로
# 재삽입하므로 중복. '## 요약'까지의 거리는 글마다 달라(TL;DR/blockquote가 끼어있기도 함)
# 고정하지 않고, H1 바로 다음 줄에 오는 "##" 헤딩인지 + 제목 텍스트가 겹치는지로만 판단한다.
DUP_HEADING_RE = re.compile(r"^#\s+(.+)\n\n##\s+(.+)\n\n")

# "## 요약" 문단 뒤, "## 본문" 앞에 오는 수동 목차 블록(컨버터가 같은 자리에 자동
# <details class="toc-details">를 삽입하므로 중복).
MANUAL_TOC_RE = re.compile(
    r"\n목차\n\n(?:- \[.+?\]\(#.+?\)\n\n)+(?=##\s+본문)",
    re.MULTILINE,
)


def strip_legacy_blocks(body):
    """(new_body, heading_removed, toc_removed) 반환. 매치 안 되면 각각 False."""
    heading_removed = False
    toc_removed = False

    def _heading_sub(m):
        nonlocal heading_removed
        h1_title, h2_title = m.group(1).strip(), m.group(2).strip()
        if h2_title and (h2_title in h1_title or h1_title.startswith(h2_title)):
            heading_removed = True
            return f"# {h1_title}\n\n"
        return m.group(0)

    new_body = DUP_HEADING_RE.sub(_heading_sub, body, count=1)

    def _toc_sub(m):
        nonlocal toc_removed
        toc_removed = True
        return "\n"

    new_body = MANUAL_TOC_RE.sub(_toc_sub, new_body, count=1)

    return new_body, heading_removed, toc_removed


def get_blogger_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["BLOGGER_CLIENT_ID"],
        client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
    )
    return build("blogger", "v3", credentials=credentials)


def find_affected():
    affected = []
    for path in all_post_paths():
        post = frontmatter.load(path)
        if post.metadata.get("status") != "published":
            continue
        new_body, heading_removed, toc_removed = strip_legacy_blocks(post.content)
        if heading_removed or toc_removed:
            affected.append((path, post, new_body, heading_removed, toc_removed))
    return affected


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", action="store_true")
    group.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    affected = find_affected()
    if not affected:
        print("영향받는 글이 없습니다.")
        return

    print(f"{len(affected)}개 글에서 레거시 중복 블록 발견:\n")
    for path, post, new_body, heading_removed, toc_removed in affected:
        rel = path.relative_to(path.parent.parent)
        marks = []
        if heading_removed:
            marks.append("중복 제목")
        if toc_removed:
            marks.append("수동 목차")
        print(f"  [{'/'.join(marks)}] {rel}")

    if args.scan:
        return

    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    service = None if args.dry_run else get_blogger_service()

    print()
    for path, post, new_body, heading_removed, toc_removed in affected:
        rel = path.relative_to(path.parent.parent)
        tag = "[DRY-RUN]" if args.dry_run else "[APPLY]"
        print(f"{tag} {rel}")

        if args.dry_run:
            continue

        new_post = frontmatter.Post(new_body, **post.metadata)
        path.write_text(frontmatter.dumps(new_post), encoding="utf-8")
        print(f"       로컬 파일 저장 완료")

        post_id = post.metadata.get("id")
        if not post_id:
            print(f"       [경고] frontmatter에 id 없음 - 라이브 반영 생략")
            continue

        conversion = convert_markdown_to_html(new_body)
        title = post.metadata.get("title", rel.stem)
        tags = post.metadata.get("tags", [])
        service.posts().update(
            blogId=blog_id,
            postId=post_id,
            body={"title": title, "content": conversion["html"], "labels": tags},
        ).execute()
        print(f"       라이브 게시물 {post_id} 갱신 완료")

    verb = "시뮬레이션" if args.dry_run else "완료"
    print(f"\n총 {len(affected)}개 글 {verb}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
