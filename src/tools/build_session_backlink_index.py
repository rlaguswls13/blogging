"""
wiki/sessions/raw/*.md(각 최대 2.7MB) 안의 개별 세션 블록 위치를 줄 범위(line range)로 인덱싱하는 도구.

배경: 2026-08-22 문서 개편 전에는 wiki 문서 8개가 "## 관련 세션"에서 파일 전체(최대 2.7MB)를
가리켰다 — 실제로 필요한 정보는 그 파일의 일부 블록뿐인데도 파일 단위로만 연결되어 있었다.
이 도구는 각 raw 아카이브를 블록 단위(`### 세션 기록 (YYYY-MM-DD HH:MM:SS)` 헤더 기준)로 파싱해
파일마다 (시작줄, 끝줄, 태그)를 계산하고 wiki/sessions/raw-index.json에 기록한다. wiki 문서는 이제
파일 전체가 아니라 `wiki/sessions/raw/2026-08-16.md:1234-1567` 같은 구체적 줄 범위를 backlink로 쓸 수
있고, 이 범위만 Read(offset=, limit=)로 읽으면 파일 전체를 열 필요가 없다.

이 스크립트 자체는 Python으로 디스크에서 직접 파일을 읽으므로(에이전트의 대화 컨텍스트를 거치지
않음) 파일 크기와 무관하게 안전하게 실행된다.

wiki/sessions/raw/*.md를 만든 src/tools/split_session_history.py의 KEYWORD_TAGS를 그대로 재사용해
태그 매칭 기준을 하나로 유지한다.

사용법:
  python src/tools/build_session_backlink_index.py [--dry-run]
      wiki/sessions/raw-index.json을 생성/갱신한다. --dry-run이면 통계만 출력하고 파일을 쓰지 않는다.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SESSIONS_RAW_DIR = REPO_ROOT / "wiki" / "sessions" / "raw"
INDEX_PATH = REPO_ROOT / "wiki" / "sessions" / "raw-index.json"

sys.path.insert(0, str(REPO_ROOT))
from src.tools.split_session_history import KEYWORD_TAGS  # noqa: E402

BLOCK_HEADER = re.compile(r"^### 세션[^\n]*\((\d{4}-\d{2}-\d{2})[^)]*\)")


def tags_for_text(text: str):
    return sorted({tag for keyword, tag in KEYWORD_TAGS.items() if keyword in text})


def index_file(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    total = len(lines)

    headers = []  # (line_no_1_indexed, date)
    for i, line in enumerate(lines, start=1):
        m = BLOCK_HEADER.match(line)
        if m:
            headers.append((i, m.group(1)))

    blocks = []
    for idx, (start, date) in enumerate(headers):
        end = headers[idx + 1][0] - 1 if idx + 1 < len(headers) else total
        block_text = "\n".join(lines[start - 1:end])
        blocks.append({
            "startLine": start,
            "endLine": end,
            "date": date,
            "tags": tags_for_text(block_text),
        })

    return total, blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not SESSIONS_RAW_DIR.exists():
        print(f"오류: {SESSIONS_RAW_DIR} 없음.", file=sys.stderr)
        sys.exit(1)

    files = {}
    tag_index = {}
    for path in sorted(SESSIONS_RAW_DIR.glob("*.md")):
        total, blocks = index_file(path)
        files[path.name] = {"totalLines": total, "blocks": blocks}
        for b in blocks:
            for tag in b["tags"]:
                tag_index.setdefault(tag, []).append({
                    "file": path.name,
                    "startLine": b["startLine"],
                    "endLine": b["endLine"],
                    "date": b["date"],
                })
        print(f"{path.name}: {total}줄, 블록 {len(blocks)}개")

    # 태그별로 최신 날짜 우선 정렬
    for tag in tag_index:
        tag_index[tag].sort(key=lambda e: (e["date"], e["file"]), reverse=True)

    index = {
        "version": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "files": files,
        "tagIndex": tag_index,
    }

    if args.dry_run:
        print(f"\n[DRY-RUN] {INDEX_PATH.relative_to(REPO_ROOT)}에 쓸 내용 미리보기만 출력했습니다 (변경 없음).")
        return

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n완료: {INDEX_PATH.relative_to(REPO_ROOT)} 생성/갱신.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
