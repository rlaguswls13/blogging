import datetime
import os
import re
import subprocess
import frontmatter
from typing import List, Dict, Any
from src.core.paths import run_directory, posts_root, project_root, post_path_for, find_post_by_slug
from src.core.files import read_state, write_json
from src.core.types import TailQuestion, Reference, TocItem, KnowledgeNode, PublishedPlatformDetail, Backlink
from src.pipeline.validate import validate_run
from src.pipeline.converter import convert_markdown_to_html
from src.publishers.base import BlogPublisher, ArticlePayload, PublishResult
from src.publishers.notion import NotionPublisher
from src.publishers.blogger import BloggerPublisher


def ensure_images_pushed() -> None:
    """content/images/에 미반영 변경이 있으면 커밋 후 원격으로 push한다.

    convert_markdown_to_html()이 로컬 이미지를 GitHub Raw CDN URL로 치환하는데,
    이 URL은 해당 파일이 실제로 원격 저장소에 push되어 있어야만 살아있다.
    push하지 않은 채 발행하면 라이브 게시물의 이미지 링크가 깨진 채로 나가므로,
    발행 직전에 이를 자동으로 맞춘다. 실패 시 예외를 던져 발행 자체를 차단한다.
    """
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "content/images/"],
        cwd=project_root, capture_output=True, text=True, check=True
    )
    if not status.stdout.strip():
        return

    print("[이미지 동기화] content/images/에 미반영 변경을 발견했습니다. 커밋 및 push를 진행합니다...")
    subprocess.run(["git", "add", "content/images/"], cwd=project_root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore(images): sync content/images before publish"],
        cwd=project_root, check=True
    )
    subprocess.run(["git", "push"], cwd=project_root, check=True)
    print("[이미지 동기화] push 완료.")

def get_publisher(platform: str) -> BlogPublisher:
    if platform == "blogger":
        return BloggerPublisher()
    elif platform == "notion":
        return NotionPublisher()
    else:
        raise ValueError(f"지원하지 않는 플랫폼입니다: {platform}")

def parse_tail_questions(markdown_content: str, article_id: str) -> List[TailQuestion]:
    match = re.search(r"## 꼬리질문\s*$(.*?)(?=##|\Z)", markdown_content, re.MULTILINE | re.DOTALL)
    if not match:
        return []

    section_content = match.group(1)
    lines = section_content.split('\n')
    questions = []
    index = 1

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        clean_line = re.sub(r"^(?:\d+\.|[-*])\s*(?:\[\s*\])?\s*", "", trimmed).strip()
        if not clean_line:
            continue

        url_matches = re.findall(r"https?://[^\s)]+", clean_line)

        question_text = re.sub(r"\(?(?:추천\s*)?URL:\s*https?://[^\s)]+\)?", "", clean_line, flags=re.IGNORECASE)
        question_text = re.sub(r"https?://[^\s)]+", "", question_text)
        question_text = re.sub(r"\(\s*\)", "", question_text).strip()

        questions.append(TailQuestion(
            id=f"q-{article_id}-{index}",
            question=question_text if question_text else clean_line,
            relatedTocIds=[],
            suggestedUrls=url_matches,
            status="todo"
        ))
        index += 1

    return questions

def parse_references(markdown_content: str) -> List[Reference]:
    match = re.search(r"## 참고문헌\s*$(.*?)(?=##|\Z)", markdown_content, re.MULTILINE | re.DOTALL)
    if not match:
        return []

    section_content = match.group(1)
    lines = section_content.split('\n')
    refs = []
    index = 1

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        clean_line = re.sub(r"^(?:\d+\.|[-*])\s*", "", trimmed).strip()
        if not clean_line:
            continue

        link_match = re.search(r"\[([^\]]+)\]\((https?://[^\)]+)\)", clean_line)
        if link_match:
            refs.append(Reference(
                id=f"ref-{index}",
                title=link_match.group(1),
                url=link_match.group(2),
                tocItemId=""
            ))
            index += 1
        else:
            url_match = re.search(r"(https?://\S+)", clean_line)
            if url_match:
                url = url_match.group(1)
                title = clean_line.replace(url, "").strip()
                refs.append(Reference(
                    id=f"ref-{index}",
                    title=title if title else "참고 자료",
                    url=url,
                    tocItemId=""
                ))
                index += 1

    return refs

def parse_toc_items(markdown_content: str) -> List[TocItem]:
    lines = markdown_content.split('\n')
    items = []
    index = 1
    in_code_block = False

    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        match = re.match(r"^(#{2,3})\s+(.+)$", line)
        if match:
            depth = len(match.group(1))
            title = match.group(2).strip()
            items.append(TocItem(
                id=f"toc-{index}",
                title=title,
                level=depth
            ))
            index += 1

    return items

def publish_to_multi(run_id: str, platforms: List[str], dry_run: bool) -> None:
    if "blogger" in platforms:
        platforms = ["blogger"] + [p for p in platforms if p != "blogger"]

    ok, errors, warnings = validate_run(run_id, require_human_approval=not dry_run)
    if not ok:
        raise Exception(f"게시 게이트 통과 실패:\n- " + "\n- ".join(errors))

    for w in warnings:
        print(f"경고: {w}")

    if not dry_run:
        ensure_images_pushed()

    dir_path = run_directory(run_id)
    state_path = dir_path / "state.json"
    state = read_state(state_path)

    with open(dir_path / "final.md", "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    content = post.content
    metadata = post.metadata

    # 꼬리질문 strip과 bare URL linkify는 convert_markdown_to_html() 내부에서 일괄 처리한다 —
    # 이 함수를 우회해서 직접 convert_markdown_to_html()를 호출하는 다른 도구들도 동일하게
    # 적용받게 하기 위함(2026-08-23, src/pipeline/converter.py 참고).
    conversion = convert_markdown_to_html(content)

    tags = metadata.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    results = []
    published_platforms = state.publishedPlatforms if state.publishedPlatforms else {}

    for p in platforms:
        publisher = get_publisher(p)

        existing_post_id = None
        if p == "notion":
            existing_post_id = state.notionPageId or (published_platforms.get(p).postId if published_platforms.get(p) else None)
        else:
            existing_post_id = published_platforms.get(p).postId if published_platforms.get(p) else None

        payload = ArticlePayload(
            title=metadata.get("title", state.topic),
            markdownContent=content,
            htmlContent=conversion["html"],
            tags=tags,
            existingPostId=existing_post_id
        )

        print(f"[게시 시작] 플랫폼: {p}")
        result = publisher.publish(payload, dry_run)
        results.append(result)
        print(f"[게시 완료] 플랫폼: {p}, ID: {result.postId}")

    if dry_run:
        print("Dry-run 완료. 실제 상태를 업데이트하지 않습니다.")
        return

    tail_questions = parse_tail_questions(content, state.articleId)
    references = parse_references(content)
    toc_items = parse_toc_items(content)

    updated_platforms = {**published_platforms}
    for r in results:
        updated_platforms[r.platform] = PublishedPlatformDetail(
            postId=r.postId,
            url=r.url,
            publishedAt=r.publishedAt
        )
        if r.platform == "notion":
            state.notionPageId = r.postId

    state.status = "published"
    state.tailQuestions = tail_questions
    state.publishedPlatforms = updated_platforms
    state.updatedAt = datetime.datetime.utcnow().isoformat() + "Z"

    write_json(state_path, state)

    write_json(dir_path / "publish-result.json", {
        "runId": run_id,
        "results": [r.model_dump() for r in results],
        "publishedAt": state.updatedAt
    })

    # 관리자 승인 및 게시 완료된 final.md 포스팅 원본을 content/posts/ 정식 자산 저장소로 이관.
    # slug는 state.json이 아니라 final.md 자체 frontmatter를 신뢰 소스로 삼는다 —
    # state.slug는 어디서도 채워지지 않아 항상 None이라, 이전에는 매번 articleId로
    # 떨어져 content/posts/의 다른 글들과 파일명 규칙이 어긋났다(2026-08-17 발견).
    slug_val = metadata.get("slug") or state.articleId
    tags_val = metadata.get("tags") or []

    blogger_result = next((r for r in results if r.platform == "blogger"), results[0] if results else None)
    archived_metadata = dict(metadata)
    archived_metadata["status"] = "published"
    if blogger_result:
        # id도 내부 articleId가 아니라 실제 Blogger post ID로 덮어써야 한다 — 다른 도구
        # (src/tools/patch_published_posts.py, update_post_content.py 등)가 이 id 필드를
        # Blogger API 호출의 postId로 그대로 사용하기 때문에, articleId가 남아있으면
        # 이후 그 글에 대한 모든 API 기반 유지보수 작업이 깨진다(2026-08-17 발견).
        archived_metadata["id"] = blogger_result.postId
        archived_metadata["url"] = blogger_result.url
        archived_metadata["publishedAt"] = blogger_result.publishedAt

    # content/posts/에는 sanitize된 published_content가 아니라 원본 final.md 본문(content)을
    # 그대로 보관한다 — wiki/Blog_Writing_Rules.md 6번 수칙("원본을 최종 승인 포스팅으로서
    # 이관 보관")과 일치시키기 위함. 내부 검증 메모(## 사실 검증 결과 등) 제거는 라이브 HTML
    # 변환(convert_markdown_to_html) 단계에서만 이루어지고, 로컬 아카이브는 원본 그대로 유지된다.
    archived_post = frontmatter.Post(content, **archived_metadata)
    # 이전에 다른 카테고리로 이미 이관된 적이 있으면(재발행/카테고리 변경) 그 자리를 갱신하고,
    # 없으면 태그 기준으로 새 카테고리 폴더(Basics/Advanced/ETC)에 저장한다.
    dest_path = find_post_by_slug(slug_val) or post_path_for(slug_val, tags_val)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        frontmatter.dump(archived_post, f)
    rel_path = dest_path.relative_to(posts_root)
    print(f"[자산 이관 완료] final.md -> content/posts/{rel_path}")

    print("모든 플랫폼 게시 완료 및 content/posts/에 최종 저장되었습니다.")
