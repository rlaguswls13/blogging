"""
.agent/session-handoff.md의 `## Session log` 섹션을 정리하는 재사용 가능한 유지보수 도구.

배경: session-handoff 스킬(전역, ~/.claude/skills/session-handoff) 자체 규칙은 "Session log에는
체크포인트마다 한 줄만 append"인데, 실제로는 세션마다 여러 문장짜리 문단을 통째로 추가해와
2026-08-22 기준 파일이 26KB까지 불어났다(세션 시작마다 전체를 읽으므로 매번 그만큼의 토큰을 태움).
이 도구는 최신 --keep개만 handoff 파일에 남기고 나머지를 wiki/sessions/changelog.md로 옮긴다
(요약하지 않고 원문 그대로 이동 — 감사 추적성 손실 없음). --dry-run을 지원하는 이 저장소의 기존
유지보수 도구 관례(apply_nav_labels.py 등, wiki/Agent_Guidelines.md 참고)를 따른다.

사용법:
  python src/tools/archive_session_log.py --dry-run [--keep N]
      옮겨질 항목 수와 미리보기만 출력한다 (변경 없음).

  python src/tools/archive_session_log.py [--keep N]
      실제로 .agent/session-handoff.md를 갱신하고 wiki/sessions/changelog.md에 append한다.
      기본 --keep 3.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HANDOFF_PATH = REPO_ROOT / ".agent" / "session-handoff.md"
CHANGELOG_PATH = REPO_ROOT / "wiki" / "sessions" / "changelog.md"

SECTION_HEADING = "## Session log"
CHANGELOG_HEADER = (
    "# Session Log Changelog\n\n"
    "`.agent/session-handoff.md`의 Session log 섹션에서 `src/tools/archive_session_log.py`로\n"
    "옮겨진 과거 체크포인트 기록입니다(요약이 아니라 원문 그대로 이동). 최신 항목은\n"
    "`.agent/session-handoff.md`를 참고하세요.\n\n"
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep", type=int, default=3, help="handoff 파일에 남길 최신 항목 수 (기본 3)")
    return parser.parse_args()


def split_session_log(text: str):
    """(머리말, Session log 헤딩 앞까지, 항목 리스트) 반환. 헤딩이 없으면 (text, None, [])."""
    idx = text.find(SECTION_HEADING)
    if idx == -1:
        return text, None, []
    head = text[:idx]
    rest = text[idx + len(SECTION_HEADING):]
    entries = [line for line in rest.splitlines() if line.strip().startswith("- ")]
    return head, SECTION_HEADING, entries


def main():
    args = parse_args()

    if not HANDOFF_PATH.exists():
        print(f"오류: {HANDOFF_PATH} 없음.", file=sys.stderr)
        sys.exit(1)

    text = HANDOFF_PATH.read_text(encoding="utf-8")
    head, heading, entries = split_session_log(text)

    if heading is None:
        print("오류: '## Session log' 섹션을 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    if len(entries) <= args.keep:
        print(f"항목 {len(entries)}개 <= --keep {args.keep} — 옮길 항목이 없습니다.")
        return

    to_archive = entries[: len(entries) - args.keep]
    to_keep = entries[len(entries) - args.keep:]

    print(f"전체 {len(entries)}개 항목 중 {len(to_archive)}개를 {CHANGELOG_PATH.relative_to(REPO_ROOT)}로 이동, "
          f"{len(to_keep)}개는 {HANDOFF_PATH.relative_to(REPO_ROOT)}에 유지합니다.")
    for line in to_archive:
        print(f"  {'[DRY-RUN] ' if args.dry_run else ''}이동: {line[:80]}")

    if args.dry_run:
        print("\n[DRY-RUN] 여기까지 미리보기입니다. 실제 적용하려면 --dry-run 없이 재실행하세요.")
        return

    # 1. changelog.md에 append (없으면 헤더와 함께 생성)
    CHANGELOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CHANGELOG_PATH.exists():
        changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    else:
        changelog = CHANGELOG_HEADER
    if not changelog.endswith("\n"):
        changelog += "\n"
    changelog += "\n".join(to_archive) + "\n"
    CHANGELOG_PATH.write_text(changelog, encoding="utf-8")

    # 2. handoff 파일의 Session log 섹션을 최신 --keep개만 남기고 재작성
    new_text = head.rstrip("\n") + "\n\n" + SECTION_HEADING + "\n" + "\n".join(to_keep) + "\n"
    HANDOFF_PATH.write_text(new_text, encoding="utf-8")

    print(f"\n완료: {CHANGELOG_PATH.relative_to(REPO_ROOT)}에 {len(to_archive)}건 추가, "
          f"{HANDOFF_PATH.relative_to(REPO_ROOT)}에 {len(to_keep)}건 유지.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
