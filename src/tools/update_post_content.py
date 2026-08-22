"""
이미 발행된 content/posts/<slug>.md의 본문을 다시 작성해 로컬 파일과 라이브 Blogger
게시물 양쪽에 반영하는 유지보수 도구.

배경: 이 파이프라인은 새 글을 만드는 경로(python main.py new/validate/approve/publish)만
있고, 이미 발행된 글의 본문을 나중에 통째로 갱신하는 CLI 경로가 없다(원본 temp/runs/
실행 폴더는 발행 후 정리되어 사라짐). 2026-08-17 GoF 디자인 패턴 시리즈를 표준 8섹션
템플릿으로 통일하면서 이 공백이 발견되어 만든 도구.

동작:
  1. content/posts/<slug>.md를 읽어 frontmatter는 그대로 두고 본문만 --body-file 내용으로
     교체한다.
  2. src/pipeline/converter.py::convert_markdown_to_html()으로 HTML을 재생성한다.
  3. frontmatter의 id를 Blogger post ID로 사용해 posts.update()로 라이브 게시물 본문을
     교체한다.

사용법:
  python src/tools/update_post_content.py --slug <slug> --body-file <path> --dry-run
      로컬 파일 교체 결과와 (라이브 patch 없이) 생성될 HTML 길이 등만 미리 보여준다.

  python src/tools/update_post_content.py --slug <slug> --body-file <path>
      실제로 로컬 파일을 덮어쓰고 라이브 게시물까지 갱신한다.

  python src/tools/update_post_content.py --slug <slug> --body-file <path> --title "새 제목"
      본문뿐 아니라 frontmatter/라이브 게시물의 제목도 함께 바꾼다.

--body-file은 frontmatter 없이 "# 제목" 이후 본문 마크다운만 담은 파일이어야 한다
(frontmatter는 기존 content/posts/<slug>.md의 것을 그대로 보존한다 — title도 마찬가지이므로,
본문의 "# 제목"과 기존 frontmatter title이 다르면 --title 없이는 라이브 제목이 옛날 것 그대로
남는다는 점에 주의. 다르면 경고를 출력해준다).
"""

import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import frontmatter
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.core.paths import find_post_by_slug
from src.pipeline.converter import convert_markdown_to_html

load_dotenv()


def get_service():
    client_id = os.environ["BLOGGER_CLIENT_ID"]
    client_secret = os.environ["BLOGGER_CLIENT_SECRET"]
    refresh_token = os.environ["BLOGGER_REFRESH_TOKEN"]
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    return build("blogger", "v3", credentials=credentials)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if "--slug" not in sys.argv or "--body-file" not in sys.argv:
        print("사용법: python src/tools/update_post_content.py --slug <slug> --body-file <path> [--dry-run]", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[sys.argv.index("--slug") + 1]
    body_file = sys.argv[sys.argv.index("--body-file") + 1]
    dry_run = "--dry-run" in sys.argv

    post_path = find_post_by_slug(slug)
    if post_path is None:
        print(f"Error: content/posts/*/{slug}.md 없음", file=sys.stderr)
        sys.exit(1)

    existing = frontmatter.loads(post_path.read_text(encoding="utf-8"))
    new_body = open(body_file, "r", encoding="utf-8").read()

    # frontmatter의 title은 본문만 교체해서는 자동으로 안 바뀐다. 새 본문의 H1과
    # 기존 title이 다르면 Blogger에 옛 제목이 그대로 나갈 수 있으니 미리 경고한다
    # (2026-08-17 GoF 시리즈 통일 작업 중 실제로 3개 글에서 발생했던 문제).
    h1_match = re.search(r"^#\s+(.+)$", new_body, re.MULTILINE)
    if h1_match:
        new_h1 = h1_match.group(1).strip()
        old_title = str(existing.metadata.get("title", "")).strip()
        if new_h1 != old_title:
            print(f"[경고] frontmatter title과 새 본문 H1이 다릅니다.")
            print(f"       기존 title: {old_title}")
            print(f"       새 본문 H1: {new_h1}")
            print(f"       title도 갱신하려면 --title \"{new_h1}\" 옵션을 추가하세요.")

    if "--title" in sys.argv:
        existing.metadata["title"] = sys.argv[sys.argv.index("--title") + 1]

    new_post = frontmatter.Post(new_body, **existing.metadata)
    new_text = frontmatter.dumps(new_post)

    tag = "[DRY-RUN]" if dry_run else "[APPLY]"
    print(f"{tag} {slug}: 본문 {len(new_body)}자로 교체")

    conversion = convert_markdown_to_html(new_body)
    print(f"{tag} 생성된 HTML {len(conversion['html'])}자")

    if dry_run:
        return

    post_path.write_text(new_text, encoding="utf-8")
    print(f"로컬 파일 저장 완료: {post_path}")

    post_id = existing.metadata.get("id")
    if not post_id:
        print("경고: frontmatter에 id 없음 - 라이브 반영 생략")
        return

    blog_id = os.environ["BLOGGER_BLOG_ID"]
    service = get_service()
    tags = existing.metadata.get("tags", [])
    title = existing.metadata.get("title", slug)

    service.posts().update(
        blogId=blog_id,
        postId=post_id,
        body={"title": title, "content": conversion["html"], "labels": tags},
    ).execute()
    print(f"라이브 게시물 {post_id} 갱신 완료")


if __name__ == "__main__":
    main()
