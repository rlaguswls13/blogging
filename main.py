import sys
import os
from typing import List, Optional
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from src.pipeline.new_run import create_run
from src.pipeline.validate import validate_run
from src.pipeline.seo_check import check_meta_description
from src.pipeline.approve import approve_run
from src.publishers import publish_to_multi
from src.pipeline.sync_mdx import sync_mdx
from src.pipeline.knowledge_store import get_todos, load_knowledge_graph
from src.theme.theme import manage_theme

def read_flag(args: List[str], name: str) -> Optional[str]:
    for i, arg in enumerate(args):
        if arg == f"--{name}" and i + 1 < len(args):
            return args[i+1]
        if arg.startswith(f"--{name}="):
            return arg.split("=", 1)[1]
    return None

def has_flag(args: List[str], name: str) -> bool:
    return f"--{name}" in args

def required_flag(args: List[str], name: str) -> str:
    val = read_flag(args, name)
    if val is None:
        print(f"Error: 필수 옵션이 누락되었습니다: --{name}", file=sys.stderr)
        sys.exit(1)
    return val

def main():
    if len(sys.argv) < 2:
        print("사용법: python main.py <new|validate|approve|publish|sync|todo|backlinks|theme> [options]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    try:
        if command == "new":
            topic = required_flag(args, "topic")
            run_id = create_run(topic)
            print(f"새 실행 생성: {run_id}")
            print(f"경로: temp/runs/{run_id}")
            return

        elif command == "validate":
            run_id = required_flag(args, "run")
            preflight = has_flag(args, "preflight")
            skip_link_check = has_flag(args, "skip-link-check")
            ok, errors, warnings = validate_run(
                run_id,
                require_human_approval=not preflight,
                skip_link_check=skip_link_check
            )

            for w in warnings:
                print(f"경고: {w}")
            if not ok:
                for e in errors:
                    print(f"오류: {e}", file=sys.stderr)
                sys.exit(1)
            print("게시 게이트 통과")

            if has_flag(args, "seo"):
                # 8개 발행 게이트(validate_run())와 완전히 분리된 독립 점검 — 통과 실패해도
                # 발행 게이트 자체를 막지 않는다(현재는 정보/경고 수준).
                seo_result = check_meta_description(run_id)
                print(f"\n[SEO] 라이브 메타 description 예상 미리보기 ({len(seo_result.snippet_preview)}자):")
                print(f"[SEO]   \"{seo_result.snippet_preview}\"")
                for w in seo_result.warnings:
                    print(f"[SEO] 경고: {w}")
                if seo_result.ok:
                    print("[SEO] 점검 통과 — 경고 없음")
            return

        elif command == "approve":
            run_id = required_flag(args, "run")
            approve_run(run_id)
            print(f"사람 승인 기록 완료: {run_id}")
            return

        elif command == "publish":
            run_id = required_flag(args, "run")
            platform_str = read_flag(args, "platform") or "blogger"
            platforms = [p.strip() for p in platform_str.split(",")]
            dry_run = has_flag(args, "dry-run")

            publish_to_multi(run_id, platforms, dry_run)
            print("dry-run 완료" if dry_run else "멀티 플랫폼 게시 완료")
            return

        elif command == "sync":
            count = sync_mdx()
            print(f"{count}개의 Notion 페이지를 MDX로 생성했습니다.")
            return

        elif command == "todo":
            status = read_flag(args, "status")
            todos = get_todos(status)
            print(f"--- 꼬리질문 TODO 목록 ({status if status else '전체'}) ---")
            if not todos:
                print("미완료된 꼬리질문이 없습니다.")
            else:
                for item in todos:
                    todo = item["todo"]
                    print(f"[{todo.status.upper()}] ID: {todo.id}")
                    print(f"  질문: {todo.question}")
                    print(f"  출처 글: {item['topic']} (ID: {item['articleId']})")
                    if todo.suggestedUrls:
                        print(f"  추천 URL: {', '.join(todo.suggestedUrls)}")
                    if todo.linkedArticleId:
                        print(f"  연결된 글 ID: {todo.linkedArticleId}")
                    print("")
            return

        elif command == "backlinks":
            graph = load_knowledge_graph()
            run_id = required_flag(args, "run")
            target_article_id = f"article-{run_id}"

            node = next((n for n in graph.get("nodes", []) if n.get("articleId") == target_article_id), None)
            if not node:
                print(f"오류: 지식 그래프에서 글을 찾을 수 없습니다: {target_article_id}", file=sys.stderr)
                sys.exit(1)

            print(f"--- [{node.get('topic')}] 백링크 정보 ---")
            print(f"등록 시각: {node.get('createdAt')}")
            print("\n[인용된 참고문헌]")
            for r in node.get("references", []):
                print(f"- {r.get('title')} ({r.get('url')})")

            print("\n[설정된 백링크]")
            backlinks = node.get("backlinks", [])
            if not backlinks:
                print("설정된 백링크가 없습니다.")
            else:
                for b in backlinks:
                    print(f"- From: {b.get('fromArticleId')} -> To: {b.get('toArticleId')} (앵커: \"{b.get('anchor')}\")")
            return

        elif command == "theme":
            upload = has_flag(args, "upload")
            manage_theme(upload=upload)
            return

        else:
            print(f"Error: 지원하지 않는 명령어입니다: {command}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"오류 발생: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
