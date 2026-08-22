"""
wiki 문서에 박힌 `경로/sessions/raw/YYYY-MM-DD.md:START-END` 형식 backlink가 여전히 유효한지
검사하는 읽기 전용 lint 도구.

배경: apply_session_backlinks.py가 심어놓은 줄 범위 backlink는 wiki/sessions/raw/*.md가 나중에
수정되면(지금은 정적 아카이브라 그럴 일이 없지만) 어긋날 수 있다. 이 도구는 (1) 참조 파일이
존재하는지, (2) 줄 번호가 파일 범위 안에 있는지, (3) 시작 줄이 실제로 세션 블록 헤더(`### 세션 기록`)
줄인지(어긋남/drift 감지)를 확인해 깨진 backlink를 보고한다. 수정하지 않고 보고만 한다 — 발견되면
`apply_session_backlinks.py`를 다시 실행해 재생성할 것.

사용법:
  python src/tools/lint_session_backlinks.py
      wiki/**/*.md 전체를 스캔해 backlink 유효성을 검사하고 결과를 출력한다.
      깨진 backlink가 하나라도 있으면 exit code 1.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_DIR = REPO_ROOT / "wiki"

BACKLINK_PATTERN = re.compile(
    r"`((?:\.\./)*sessions/raw/(\d{4}-\d{2}-\d{2})\.md):(\d+)-(\d+)`"
)
BLOCK_HEADER = re.compile(r"^### 세션[^\n]*\(\d{4}-\d{2}-\d{2}")


def resolve_raw_path(doc_path: Path, rel: str) -> Path:
    # rel은 문서 기준 상대경로 (예: "../sessions/raw/2026-08-16.md" 또는 "sessions/raw/...")
    return (doc_path.parent / rel).resolve()


def lint_file(doc_path: Path):
    issues = []
    text = doc_path.read_text(encoding="utf-8")
    for m in BACKLINK_PATTERN.finditer(text):
        rel_path, date, start_s, end_s = m.groups()
        start, end = int(start_s), int(end_s)
        raw_path = resolve_raw_path(doc_path, rel_path)

        if not raw_path.exists():
            issues.append(f"{rel_path}:{start}-{end} — 파일 없음 ({raw_path})")
            continue

        lines = raw_path.read_text(encoding="utf-8").splitlines()
        total = len(lines)

        if start < 1 or end > total or start > end:
            issues.append(f"{rel_path}:{start}-{end} — 범위 오류 (파일 총 {total}줄)")
            continue

        header_line = lines[start - 1]
        if not BLOCK_HEADER.match(header_line):
            issues.append(
                f"{rel_path}:{start}-{end} — 시작 줄이 세션 블록 헤더가 아님 (drift 의심): "
                f"{header_line[:60]!r}"
            )

    return issues


def main():
    all_issues = {}
    for doc_path in sorted(WIKI_DIR.rglob("*.md")):
        if "sessions" in doc_path.relative_to(WIKI_DIR).parts:
            continue  # raw 아카이브/changelog 자체는 검사 대상 아님
        issues = lint_file(doc_path)
        if issues:
            all_issues[doc_path] = issues

    if not all_issues:
        print("모든 세션 backlink 정상 (깨진 항목 없음).")
        return

    print(f"깨진 backlink {sum(len(v) for v in all_issues.values())}건 발견:\n")
    for doc_path, issues in all_issues.items():
        print(f"{doc_path.relative_to(REPO_ROOT)}:")
        for issue in issues:
            print(f"  - {issue}")
    print("\n재생성하려면: python src/tools/build_session_backlink_index.py && "
          "python src/tools/apply_session_backlinks.py")
    sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
