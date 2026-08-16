"""
wiki/Session_History.md(전역 Gemini/Antigravity Stop 훅이 세션 종료마다 무한 prepend해서
만든 단일 raw 덤프, 2026-08-17 기준 241개 블록/4.28MB)를 날짜별 아카이브 파일
(wiki/sessions/raw/YYYY-MM-DD.md)로 분리하고, 태그 인덱스(wiki/session-graph.json)와
사람이 탐색할 인덱스 문서(wiki/Session_Index.md)를 생성하는 1회성 마이그레이션 도구.

배경: 이 파일은 이 프로젝트가 아니라 ~/.gemini/config/skills/hook/scripts/stop_handler.js
(전역 훅, git 미관리)가 만든다. 훅은 이 마이그레이션과 별개로 이미 날짜별 파일에만 쓰도록
수정됐다(향후 무한 증식 방지). 이 스크립트는 훅 수정 이전에 쌓인 기존 덤프를 같은 포맷으로
소급 변환하는 역할만 한다 — 새 일회성 스크립트가 아니라, 이미 존재하는 src/tools/*.py
유지보수 도구(patch_published_posts.py 등)와 동일하게 --dry-run을 지원하는 재사용 가능한
형태로 작성했다.

사용법:
  python src/tools/split_session_history.py --dry-run
      분리될 파일 목록, 날짜별 블록 수, 태그맵 미리보기만 출력한다 (변경 없음).

  python src/tools/split_session_history.py
      실제로 wiki/sessions/raw/*.md, wiki/Session_Index.md, wiki/session-graph.json을
      쓰고, 태그가 매칭되는 wiki 문서들에 "관련 세션" 백링크 절을 삽입한 뒤,
      원본 wiki/Session_History.md를 삭제하고 wiki/README.md의 링크를 교체한다.
      (원문은 git 이력에도 남으므로 별도 백업은 만들지 않는다.)
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
HISTORY_PATH = WIKI_DIR / "Session_History.md"
SESSIONS_RAW_DIR = WIKI_DIR / "sessions" / "raw"
INDEX_PATH = WIKI_DIR / "Session_Index.md"
GRAPH_PATH = WIKI_DIR / "session-graph.json"
README_PATH = WIKI_DIR / "README.md"

INDEX_HEADING = "## 날짜별 세션 아카이브"
TOPIC_HEADING = "## 주제별 인덱스"

# 세션 블록 텍스트에 등장하는 파일명 -> 주제 태그. wiki 문서 자체를 태깅할 때도
# 같은 맵을 재사용해(문서 파일명이 키와 겹치면 그 태그를 문서 태그로 삼음) 단일
# 소스로 일관성을 유지한다.
KEYWORD_TAGS = {
    "blogger_rules": "blogger-api",
    "blogger_platform_schema": "blogger-api",
    "Google_Blogger_API": "blogger-api",
    "blogger.py": "blogger-api",
    "auth.py": "blogger-api",
    "theme": "theme",
    ".css": "theme",
    "thema": "theme",
    "widget": "theme",
    "blog_article_pipeline_schema": "pipeline",
    "new_run.py": "pipeline",
    "main.py": "pipeline",
    "sync_published_posts": "pipeline",
    "publish_to_multi": "pipeline",
    "validate.py": "pipeline-quality",
    "publish_gate": "pipeline-quality",
    "patch_published_posts": "pipeline-quality",
    "report_fact_check_stats": "pipeline-quality",
    "update_post_content": "pipeline-quality",
    "Post_Topic_Backlog": "content-planning",
    "Blog_Writing_Rules": "content-quality",
    "Blog_Post_Template": "content-quality",
    "article.md": "content-quality",
    "Agent_Guidelines": "agent-guidelines",
    "knowledge-graph": "knowledge-graph",
    "session-handoff": "session-mgmt",
    "Session_History": "session-mgmt",
    "Session_Index": "session-mgmt",
}

BLOCK_PATTERN = re.compile(r"^### 세션[^\n]*\((\d{4}-\d{2}-\d{2})[^\n]*\)[^\n]*\n", re.MULTILINE)

# wiki 문서 경로별로 sessions/raw/ 까지의 상대 깊이가 다르므로 접두 개수를 명시한다.
BACKLINK_TARGET_DIRS = [
    WIKI_DIR,
    WIKI_DIR / "rules",
    WIKI_DIR / "theme",
    WIKI_DIR / "templates",
]


def parse_blocks(text: str):
    matches = list(BLOCK_PATTERN.finditer(text))
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        date = m.group(1)
        blocks.append((date, text[start:end]))
    return blocks


def tags_for_text(text: str):
    found = set()
    for keyword, tag in KEYWORD_TAGS.items():
        if keyword in text:
            found.add(tag)
    return found


def build_daily_files(blocks_by_date: dict):
    daily_contents = {}
    for date, blocks in blocks_by_date.items():
        header = f"# 세션 기록 — {date}\n\n"
        daily_contents[date] = header + "".join(blocks)
    return daily_contents


def build_session_graph(blocks_by_date: dict):
    tag_map = defaultdict(set)
    sessions = []
    for date, blocks in sorted(blocks_by_date.items()):
        date_tags = set()
        conv_ids = []
        for block in blocks:
            date_tags |= tags_for_text(block)
            m = re.search(r"\*\*Conversation ID\*\*: `([^`]+)`", block)
            if m:
                conv_ids.append(m.group(1))
        for tag in date_tags:
            tag_map[tag].add(date)
        sessions.append({
            "date": date,
            "count": len(blocks),
            "tags": sorted(date_tags),
            "conversationIds": conv_ids,
        })

    graph = {
        "version": "1.0.0",
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "stats": {
            "totalSessions": sum(s["count"] for s in sessions),
            "totalDates": len(sessions),
            "totalTags": len(tag_map),
        },
        "tagMap": {tag: sorted(dates, reverse=True) for tag, dates in tag_map.items()},
        "sessions": sessions,
    }
    return graph


def build_index_md(graph: dict):
    lines = [
        "# Session Index",
        "",
        "이 문서는 날짜별 세션 원본 아카이브(`sessions/raw/`)의 인덱스입니다. "
        "큐레이션된 최신 작업 상태는 [.agent/session-handoff.md](../.agent/session-handoff.md)를 참고하세요.",
        "",
        INDEX_HEADING,
    ]
    for s in sorted(graph["sessions"], key=lambda s: s["date"], reverse=True):
        tag_str = " ".join(f"`{t}`" for t in s["tags"]) if s["tags"] else ""
        suffix = f" · {tag_str}" if tag_str else ""
        lines.append(f"- [{s['date']}](sessions/raw/{s['date']}.md) — {s['count']}건{suffix}")

    lines += ["", TOPIC_HEADING]
    for tag in sorted(graph["tagMap"].keys()):
        dates = graph["tagMap"][tag]
        links = ", ".join(f"[{d}](sessions/raw/{d}.md)" for d in dates)
        lines.append(f"- **{tag}**: {links}")

    return "\n".join(lines) + "\n"


AUTO_START = "<!-- AUTO:related-sessions:start -->"
AUTO_END = "<!-- AUTO:related-sessions:end -->"


def backlink_block(doc_dir: Path, tags: set, graph: dict):
    depth_prefix = "../" if doc_dir != WIKI_DIR else ""
    dates = sorted({d for t in tags for d in graph["tagMap"].get(t, [])}, reverse=True)
    if not dates:
        return None
    lines = [AUTO_START, "", "## 관련 세션", "이 문서와 관련된 세션 아카이브(자동 생성 — 태그 매칭 기반):", ""]
    for d in dates:
        lines.append(f"- [{d}]({depth_prefix}sessions/raw/{d}.md)")
    lines += ["", AUTO_END]
    return "\n".join(lines)


def upsert_backlinks(path: Path, block: str, dry_run: bool):
    original = path.read_text(encoding="utf-8")
    if AUTO_START in original and AUTO_END in original:
        pre = original.split(AUTO_START)[0].rstrip("\n")
        post = original.split(AUTO_END)[1]
        new_content = pre + "\n\n" + block + post
    else:
        new_content = original.rstrip("\n") + "\n\n" + block + "\n"

    if new_content == original:
        return False
    print(f"  {'[DRY-RUN] ' if dry_run else ''}백링크 갱신: {path.relative_to(REPO_ROOT)}")
    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return True


def main():
    dry_run = "--dry-run" in sys.argv

    if not HISTORY_PATH.exists():
        print(f"오류: {HISTORY_PATH} 없음 — 이미 마이그레이션됐거나 경로가 다릅니다.", file=sys.stderr)
        sys.exit(1)

    text = HISTORY_PATH.read_text(encoding="utf-8")
    blocks = parse_blocks(text)
    if not blocks:
        print("오류: 세션 블록을 하나도 찾지 못했습니다 (헤더 패턴 확인 필요).", file=sys.stderr)
        sys.exit(1)

    blocks_by_date = defaultdict(list)
    for date, block in blocks:
        blocks_by_date[date].append(block)

    print(f"원본 블록 {len(blocks)}개, 날짜 {len(blocks_by_date)}개로 분리 예정:")
    for date in sorted(blocks_by_date):
        print(f"  {date}: {len(blocks_by_date[date])}건")

    daily_contents = build_daily_files(blocks_by_date)
    graph = build_session_graph(blocks_by_date)
    index_md = build_index_md(graph)

    print(f"\n태그맵 ({len(graph['tagMap'])}개 태그):")
    for tag, dates in sorted(graph["tagMap"].items()):
        print(f"  {tag}: {len(dates)}개 날짜")

    if dry_run:
        print(f"\n[DRY-RUN] 아래 파일들이 생성/삭제됩니다 (실제 변경 없음):")
        for date in daily_contents:
            print(f"  생성: {SESSIONS_RAW_DIR.relative_to(REPO_ROOT)}/{date}.md")
        print(f"  생성: {INDEX_PATH.relative_to(REPO_ROOT)}")
        print(f"  생성: {GRAPH_PATH.relative_to(REPO_ROOT)}")
        print(f"  삭제: {HISTORY_PATH.relative_to(REPO_ROOT)}")
    else:
        SESSIONS_RAW_DIR.mkdir(parents=True, exist_ok=True)
        for date, content in daily_contents.items():
            (SESSIONS_RAW_DIR / f"{date}.md").write_text(content, encoding="utf-8")
        INDEX_PATH.write_text(index_md, encoding="utf-8")
        with open(GRAPH_PATH, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
        print(f"\n생성 완료: {len(daily_contents)}개 일별 아카이브, {INDEX_PATH.name}, {GRAPH_PATH.name}")

    # 태그 매칭되는 wiki 문서에 "관련 세션" 백링크 삽입
    print("\n관련 wiki 문서 백링크 처리:")
    for doc_dir in BACKLINK_TARGET_DIRS:
        if not doc_dir.exists():
            continue
        for doc_path in sorted(doc_dir.glob("*.md")):
            if doc_path in (INDEX_PATH, HISTORY_PATH):
                continue
            doc_tags = tags_for_text(doc_path.name)
            if not doc_tags:
                continue
            block = backlink_block(doc_dir, doc_tags, graph)
            if block:
                upsert_backlinks(doc_path, block, dry_run)

    if dry_run:
        print("\n[DRY-RUN] 여기까지 미리보기입니다. 실제 적용하려면 --dry-run 없이 재실행하세요.")
        return

    # 원본 삭제 + README 링크 교체
    HISTORY_PATH.unlink()
    print(f"\n삭제 완료: {HISTORY_PATH.relative_to(REPO_ROOT)} (원문은 git 이력 + sessions/raw/*.md 에 보존)")

    if README_PATH.exists():
        readme = README_PATH.read_text(encoding="utf-8")
        old_section = "## 세션 기록\n- [세션 작업 기록](Session_History.md)"
        new_section = (
            "## 세션 기록\n"
            "- [세션 작업 기록 인덱스](Session_Index.md)\n"
            "  - 날짜별로 분리 저장되는 세션 원본 아카이브(`sessions/raw/`)의 인덱스입니다. "
            "큐레이션된 최신 작업 상태는 `.agent/session-handoff.md`를 참고하세요."
        )
        if old_section in readme:
            readme = readme.replace(old_section, new_section)
            README_PATH.write_text(readme, encoding="utf-8")
            print(f"갱신 완료: {README_PATH.relative_to(REPO_ROOT)}")
        else:
            print(f"[경고] {README_PATH.relative_to(REPO_ROOT)}에서 예상 세션 기록 섹션을 못 찾음 — 수동 확인 필요")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
