"""
wiki/sessions/raw-index.json(build_session_backlink_index.py 산출물)을 이용해 wiki 문서의
"## 관련 세션" 섹션을 파일 전체가 아닌 **구체적 줄 범위** backlink로 채우는 도구.

배경: 2026-08-22 1차 문서 개편에서는 8개 wiki 문서의 "## 관련 세션"이 최대 2.7MB짜리 raw 아카이브
파일 전체를 가리켜(잠재적 토큰 폭탄이라 실사 후 발견) 이를 `Session_Index.md` 한 줄 링크로 단순화했다.
그런데 이렇게 하면 "이 문서와 실제로 관련된 세션이 뭔지"라는 상세 정보가 사라진다. 이 도구는 그
대신 build_session_backlink_index.py가 만든 블록 단위(줄 범위) 인덱스에서 문서 태그와 일치하는
최신 블록 최대 2개를 골라 `path/to/raw/2026-08-16.md:1234-1567` 형식(이 저장소의 file_path:line_number
참조 관례)으로 적어 넣는다 — Read(offset=, limit=)로 그 범위만 읽으면 파일 전체를 열 필요가 없다.

wiki/sessions/raw/*.md 원본은 건드리지 않는다. `wiki/Session_Index.md`로의 전체 인덱스 링크도 함께
남겨 상세 탐색이 필요하면 거기서 이어갈 수 있게 한다.

사용법:
  python src/tools/apply_session_backlinks.py --dry-run
      각 문서에 어떤 backlink가 삽입될지 미리보기만 출력한다 (변경 없음).

  python src/tools/apply_session_backlinks.py
      실제로 8개 wiki 문서의 "## 관련 세션" 섹션을 갱신한다.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_PATH = WIKI_DIR / "sessions" / "raw-index.json"

sys.path.insert(0, str(REPO_ROOT))
from src.tools.split_session_history import KEYWORD_TAGS  # noqa: E402

MAX_LINKS_PER_DOC = 2

# 문서 경로(WIKI_DIR 기준 상대) -> wiki/ 루트까지의 상대 접두사
TARGET_DOCS = {
    "Blog_Writing_Rules.md": "",
    "Blog_Post_Template.md": "",
    "Google_Blogger_API_사용법.md": "",
    "templates/article.md": "../",
    "theme/blogger_layout_thema_widget.md": "../",
    "rules/blogger_rules.md": "../",
    "rules/blogger_platform_schema.md": "../",
    "rules/blog_article_pipeline_schema.md": "../",
}

SECTION_HEADING = "## 관련 세션"


def tags_for_doc(name: str):
    return sorted({tag for keyword, tag in KEYWORD_TAGS.items() if keyword in name})


def pick_blocks(tag_index: dict, tags: list):
    candidates = []
    seen = set()
    for tag in tags:
        for entry in tag_index.get(tag, []):
            key = (entry["file"], entry["startLine"], entry["endLine"])
            if key in seen:
                continue
            seen.add(key)
            candidates.append({**entry, "matchedTag": tag})
    # 최신 날짜 우선, 동일 날짜면 더 작은(더 구체적인) 블록 우선
    candidates.sort(key=lambda e: (e["date"], -(e["endLine"] - e["startLine"])), reverse=True)
    # 위 정렬은 date 내림차순 + 범위 오름차순을 동시에 만족시키기 어려우므로 2단계로 재정렬
    candidates.sort(key=lambda e: e["date"], reverse=True)
    candidates.sort(key=lambda e: (e["date"], e["endLine"] - e["startLine"]), reverse=False)
    candidates.sort(key=lambda e: e["date"], reverse=True)
    return candidates[:MAX_LINKS_PER_DOC]


def build_section(rel_prefix: str, blocks: list) -> str:
    lines = [SECTION_HEADING]
    for b in blocks:
        lines.append(
            f"- `{rel_prefix}sessions/raw/{b['file']}:{b['startLine']}-{b['endLine']}` "
            f"({b['matchedTag']}, {b['date']})"
        )
    lines.append(f"- 전체 인덱스: [Session_Index.md]({rel_prefix}Session_Index.md)")
    return "\n".join(lines)


def upsert_section(path: Path, new_section: str, dry_run: bool):
    original = path.read_text(encoding="utf-8")
    idx = original.find(SECTION_HEADING)
    if idx == -1:
        print(f"  [경고] {path.relative_to(REPO_ROOT)}에서 '{SECTION_HEADING}' 섹션을 못 찾음 — 건너뜀")
        return False
    pre = original[:idx].rstrip("\n")
    new_content = pre + "\n\n" + new_section + "\n"
    if new_content == original:
        return False
    print(f"  {'[DRY-RUN] ' if dry_run else ''}갱신: {path.relative_to(REPO_ROOT)}")
    for line in new_section.splitlines():
        print(f"      {line}")
    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not INDEX_PATH.exists():
        print(f"오류: {INDEX_PATH} 없음 — 먼저 build_session_backlink_index.py를 실행하세요.", file=sys.stderr)
        sys.exit(1)

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    tag_index = index["tagIndex"]

    for rel_path, rel_prefix in TARGET_DOCS.items():
        doc_path = WIKI_DIR / rel_path
        if not doc_path.exists():
            print(f"  [경고] {doc_path} 없음 — 건너뜀")
            continue
        tags = tags_for_doc(Path(rel_path).name)
        blocks = pick_blocks(tag_index, tags)
        if not blocks:
            print(f"  [정보] {rel_path}: 태그 매칭 블록 없음 — 건너뜀")
            continue
        section = build_section(rel_prefix, blocks)
        upsert_section(doc_path, section, args.dry_run)

    if args.dry_run:
        print("\n[DRY-RUN] 여기까지 미리보기입니다. 실제 적용하려면 --dry-run 없이 재실행하세요.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
