import datetime
import os
import re
import frontmatter
from typing import List, Dict, Any
from src.paths import run_directory
from src.files import read_state, write_json
from src.validate import validate_run
from src.converter import convert_markdown_to_html
from src.publishers.base import BlogPublisher, ArticlePayload, PublishResult
from src.publishers.notion import NotionPublisher
from src.publishers.blogger import BloggerPublisher
from src.knowledge_store import add_knowledge_node, calculate_backlinks
from src.types import TailQuestion, Reference, TocItem, KnowledgeNode, PublishedPlatformDetail, Backlink

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

def linkify_markdown(content: str) -> str:
    parts = content.split("```")
    for i in range(len(parts)):
        if i % 2 == 0:  # Non-code block
            # Match http/https URLs not preceded by ](, href=", src=", or <
            pattern = r'(?<!\]\()(?<!href=")(?<!src=")(?<!<)https?://[^\s\)\>]+'
            parts[i] = re.sub(pattern, lambda m: f"<{m.group(0)}>", parts[i])
    return "```".join(parts)

def publish_to_multi(run_id: str, platforms: List[str], dry_run: bool) -> None:
    if "blogger" in platforms:
        platforms = ["blogger"] + [p for p in platforms if p != "blogger"]

    ok, errors, warnings = validate_run(run_id, require_human_approval=not dry_run)
    if not ok:
        raise Exception(f"게시 게이트 통과 실패:\n- " + "\n- ".join(errors))

    for w in warnings:
        print(f"경고: {w}")

    dir_path = run_directory(run_id)
    state_path = dir_path / "state.json"
    state = read_state(state_path)

    with open(dir_path / "final.md", "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    content = post.content
    metadata = post.metadata

    # 1. Strip internal validation / todo checklist sections from published blog content
    published_content = content
    published_content = re.sub(r"## 사실 검증 결과\s*(.*?)(?=##|\Z)", "", published_content, flags=re.MULTILINE | re.DOTALL)
    published_content = re.sub(r"## 꼬리질문\s*(.*?)(?=##|\Z)", "", published_content, flags=re.MULTILINE | re.DOTALL)

    # 2. Automatically linkify raw URLs in markdown content (skipping code blocks)
    published_content = linkify_markdown(published_content)

    conversion = convert_markdown_to_html(published_content)

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

    backlinks = calculate_backlinks(state.articleId, state.topic)

    backlink_objs = []
    for b in backlinks:
        backlink_objs.append(Backlink(
            fromArticleId=b["fromArticleId"],
            toArticleId=b["toArticleId"],
            anchor=b["anchor"]
        ))

    add_knowledge_node(KnowledgeNode(
        articleId=state.articleId,
        topic=state.topic,
        createdAt=state.updatedAt,
        tocItems=toc_items,
        references=references,
        tailQuestions=tail_questions,
        backlinks=backlink_objs
    ))

    print("모든 플랫폼 게시 완료 및 지식 그래프에 등록되었습니다.")
