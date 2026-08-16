"""
content/posts/*.md 및 라이브 Blogger 게시물에 남아있는 유니코드 깨짐(U+FFFD, "�")을
찾아내고, 사람이 확인한 교정 내용을 로컬 파일과 라이브 게시물 양쪽에 동시 반영하는
유지보수 도구.

배경: 2026-08-17 파이프라인 신뢰도 점검 중 content/posts/*.md 40개 중 33개 파일,
총 101곳에서 U+FFFD가 발견됨. content/posts/는 src/tools/sync_published_posts.py가
Blogger 공개 피드를 그대로 받아온 결과이므로, 이 깨짐은 로컬 파일뿐 아니라 실제 라이브
Blogger 게시물에도 이미 존재한다. 정확한 발생 원인은 특정할 수 없었으나(저장소 내 모든
파일 I/O는 strict UTF-8 디코딩만 사용해 이 문자를 자체 생성할 수 없음), 지금은 원인
규명보다 실물 교정이 더 유효하다고 판단해 만든 도구.

사용법:
  python src/tools/patch_published_posts.py --find
      content/posts/*.md에서 U+FFFD 위치와 전후 문맥을 출력한다 (읽기 전용).

  python src/tools/patch_published_posts.py --apply fixes.json --dry-run
      fixes.json에 정의된 교정을 적용했을 때 무엇이 바뀌는지만 출력한다 (변경 없음).

  python src/tools/patch_published_posts.py --apply fixes.json
      로컬 content/posts/<slug>.md와, frontmatter의 id로 매칭되는 라이브 Blogger
      게시물 본문(HTML) 양쪽에 동일한 문자열 치환을 실제로 반영한다.
      라이브 패치는 전체 재렌더링이 아니라 해당 문자열만 찾아 바꾸는 최소 침습 방식이다.

fixes.json 형식:
{
  "os-process-vs-thread.md": [
    {"before": "패�� 손실", "after": "패킷 손실"}
  ]
}
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import frontmatter
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

POSTS_DIR = Path(__file__).resolve().parent.parent.parent / "content" / "posts"
CONTEXT_CHARS = 40


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


def unique_snippet(text, start, end):
    """text[start:end]가 U+FFFD 런(run)일 때, 파일 내에서 유일하게 매칭되는
    최소 길이의 앞/뒤 문맥을 붙인 스니펫을 찾아 반환한다."""
    pad = 6
    while pad <= 60:
        s = max(0, start - pad)
        e = min(len(text), end + pad)
        snippet = text[s:e]
        if text.count(snippet) == 1:
            return snippet
        pad += 6
    return text[max(0, start - 60):min(len(text), end + 60)]


def find_mode(template_out=None):
    files = sorted(POSTS_DIR.glob("*.md"))
    total = 0
    template = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        runs = list(re.finditer(r"�+", text))
        if not runs:
            continue

        print(f"\n=== {path.name} ({len(runs)}곳) ===")
        entries = []
        for m in runs:
            ctx_start = max(0, m.start() - CONTEXT_CHARS)
            ctx_end = min(len(text), m.end() + CONTEXT_CHARS)
            context = text[ctx_start:ctx_end].replace("\n", " ")
            snippet = unique_snippet(text, m.start(), m.end())
            print(f"  [런 길이 {m.end() - m.start()}] ...{context}...")
            print(f"      snippet: {snippet!r}")
            entries.append({"before": snippet, "after": "TODO"})
        template[path.name] = entries
        total += len(runs)

    print(f"\n총 {total}곳 발견 ({len(files)}개 파일 중)")

    if template_out:
        with open(template_out, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        print(f"fixes 템플릿을 {template_out} 에 저장했습니다 (after 값을 TODO에서 실제 교정으로 채울 것).")


def load_fixes(fixes_path):
    with open(fixes_path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_mode(fixes_path, dry_run):
    fixes = load_fixes(fixes_path)
    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    posts_resource = get_service().posts() if not dry_run else None

    changed_files = 0
    for filename, edits in fixes.items():
        path = POSTS_DIR / filename
        if not path.exists():
            print(f"[건너뜀] {filename}: 파일 없음")
            continue

        original_text = path.read_text(encoding="utf-8")
        post = frontmatter.loads(original_text)
        new_text = original_text
        applied_edits = []

        for edit in edits:
            before, after = edit["before"], edit["after"]
            count = new_text.count(before)
            if count != 1:
                print(f"[오류] {filename}: '{before}' 매칭 {count}건 (정확히 1건이어야 함) - 건너뜀")
                continue
            new_text = new_text.replace(before, after, 1)
            applied_edits.append(edit)

        if not applied_edits:
            continue

        tag = "[DRY-RUN]" if dry_run else "[APPLY]"
        print(f"{tag} {filename}: {len(applied_edits)}건 교정")
        for edit in applied_edits:
            print(f"       '{edit['before']}' -> '{edit['after']}'")

        if dry_run:
            changed_files += 1
            continue

        path.write_text(new_text, encoding="utf-8")

        post_id = post.metadata.get("id")
        if not post_id:
            print(f"       [경고] frontmatter에 id 없음 - 라이브 패치 생략")
            changed_files += 1
            continue

        live = posts_resource.get(blogId=blog_id, postId=post_id).execute()
        html = live.get("content", "")
        new_html = html
        live_applied = 0
        for edit in applied_edits:
            if edit["before"] in new_html:
                new_html = new_html.replace(edit["before"], edit["after"])
                live_applied += 1
            else:
                print(f"       [경고] 라이브 HTML에서 '{edit['before']}' 못 찾음 - 해당 건 생략")

        if live_applied:
            posts_resource.patch(blogId=blog_id, postId=post_id, body={"content": new_html}).execute()
            print(f"       라이브 게시물 {post_id} 패치 완료 ({live_applied}건)")

        changed_files += 1

    verb = "시뮬레이션" if dry_run else "완료"
    print(f"\n총 {changed_files}개 파일 교정 {verb}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if "--find" in sys.argv:
        template_out = None
        if "--template-out" in sys.argv:
            idx = sys.argv.index("--template-out")
            if idx + 1 < len(sys.argv):
                template_out = sys.argv[idx + 1]
        find_mode(template_out)
        return

    if "--apply" in sys.argv:
        idx = sys.argv.index("--apply")
        if idx + 1 >= len(sys.argv):
            print("Error: --apply 뒤에 fixes.json 경로를 지정해야 합니다.", file=sys.stderr)
            sys.exit(1)
        fixes_path = sys.argv[idx + 1]
        dry_run = "--dry-run" in sys.argv
        apply_mode(fixes_path, dry_run)
        return

    print("사용법: python src/tools/patch_published_posts.py <--find | --apply fixes.json [--dry-run]>", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
