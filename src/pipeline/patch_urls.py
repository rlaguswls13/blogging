from __future__ import annotations

from datetime import datetime, timezone
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Protocol, TypedDict
from urllib.parse import urlsplit

import frontmatter
from pydantic import BaseModel, ConfigDict, TypeAdapter, field_validator

from src.core.paths import find_post_by_slug, project_root
from src.publishers.blogger import BloggerPublisher


class PatchError(RuntimeError):
    pass


class UrlEdit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    before: str
    after: str

    @field_validator("before", "after")
    @classmethod
    def https_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc or any(c.isspace() for c in value):
            raise PatchError(f"Expected an absolute HTTPS URL: {value}")
        return value


class PostMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    status: str


class LivePost(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    content: str


class ContentBody(TypedDict):
    content: str


class Request(Protocol):
    def execute(self, *, num_retries: int) -> ContentBody: ...


class Posts(Protocol):
    def get(self, *, blogId: str, postId: str) -> Request: ...
    def patch(self, *, blogId: str, postId: str, body: ContentBody) -> Request: ...


class HrefParser(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.destinations: list[tuple[int, int, str]] = []
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", source)]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text()
        if raw is None:
            return
        line, column = self.getpos()
        offset = self.line_starts[line - 1] + column
        pattern = re.compile(r'''([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?''')
        for match in pattern.finditer(raw, len(tag) + 1):
            if match[1].lower() == "href":
                group = 2 if match[2] is not None else 3
                if match[group] is not None:
                    self.destinations.append((offset + match.start(group), offset + match.end(group), html.unescape(match[group])))


def replace_destinations(text: str, edits: list[UrlEdit], *, live: bool) -> str:
    """Replace exact destinations, rejecting missing or ambiguous links first."""
    if live:
        parser = HrefParser(text)
        parser.feed(text)
        destinations = parser.destinations
    else:
        destinations = [(m.start(1), m.end(1), m[1]) for m in re.finditer(r"\]\(([^\s]+)\)", text)]
    replacements: list[tuple[int, int, str]] = []
    for edit in edits:
        old = [m for m in destinations if m[2] == edit.before]
        new = [m for m in destinations if m[2] == edit.after]
        if len(old) == 1 and not new:
            match = old[0]
            replacement = html.escape(edit.after, quote=True) if live else edit.after
            replacements.append((match[0], match[1], replacement))
        elif not old and len(new) == 1:
            continue
        else:
            raise PatchError(f"Missing/ambiguous destination: {edit.before} (before={len(old)}, after={len(new)})")
    for start, end, value in sorted(replacements, reverse=True):
        text = text[:start] + value + text[end:]
    return text


def patch_urls(slug: str, edits_file: Path, dry_run: bool = False) -> None:
    """Apply one validated destination-only patch, without OAuth fallback or retries."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
        raise PatchError("Invalid article slug")
    edits = TypeAdapter(list[UrlEdit]).validate_json(edits_file.read_bytes())
    urls = [url for edit in edits for url in (edit.before, edit.after)]
    if not edits or len(set(urls)) != len(urls):
        raise PatchError("Edits must be nonempty with distinct before/after URLs")
    path = find_post_by_slug(slug)
    if path is None:
        raise PatchError(f"Article not found: {slug}")
    original = path.read_bytes()
    local = original.decode("utf-8")
    metadata = PostMetadata.model_validate(frontmatter.loads(local).metadata)
    if metadata.status != "published" or not metadata.id.isdecimal():
        raise PatchError("Article must have a published Blogger post ID")
    updated_local = replace_destinations(local, edits, live=False)
    publisher = BloggerPublisher()
    credentials = publisher.get_credentials(require_refresh_token=True)
    posts: Posts = publisher.get_blogger_service(credentials).posts()
    blog_id = credentials["blog_id"]
    live = LivePost.model_validate(posts.get(blogId=blog_id, postId=metadata.id).execute(num_retries=0))
    if live.id != metadata.id:
        raise PatchError("Blogger response ID mismatch")
    expected = replace_destinations(live.content, edits, live=True)
    if dry_run:
        print(f"[patch-urls dry-run] ID: {metadata.id}, URLs: {len(edits)}, live change: {expected != live.content}")
        return
    backup = project_root / "temp" / "backups" / f"patch-urls-{metadata.id}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}"
    backup.mkdir(parents=True, exist_ok=False)
    (backup / "local.md").write_bytes(original)
    (backup / "live.json").write_text(live.model_dump_json(), encoding="utf-8")
    (backup / "edits.json").write_text(json.dumps([edit.model_dump() for edit in edits], ensure_ascii=False, indent=2), encoding="utf-8")
    if expected != live.content:
        posts.patch(blogId=blog_id, postId=metadata.id, body={"content": expected}).execute(num_retries=0)
        verified = LivePost.model_validate(posts.get(blogId=blog_id, postId=metadata.id).execute(num_retries=0))
        if verified.id != metadata.id or verified.content != expected:
            raise PatchError(f"Live verification failed; backup: {backup}")
    if updated_local != local:
        path.write_bytes(updated_local.encode("utf-8"))
    print(f"[patch-urls] ID: {metadata.id}, URLs: {len(edits)}, success; backup: {backup}")
