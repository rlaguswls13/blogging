from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Final

import frontmatter
from src.core.files import read_state
from src.core.paths import all_post_paths, project_root, run_directory
from src.pipeline.seo_check import _extract_section, check_meta_description, markdown_to_plain


if TYPE_CHECKING:
    from playwright.sync_api import Page


DESCRIPTION_LIMIT: Final = 150
MAX_ATTEMPTS: Final = 5


class SeoMetaError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SeoMetaPlan:
    run_id: str
    blog_id: str
    post_id: str
    description: str

    @property
    def editor_url(self) -> str:
        return f"https://www.blogger.com/blog/post/edit/{self.blog_id}/{self.post_id}"


def build_seo_meta_plan(run_id: str, blog_id: str) -> SeoMetaPlan:
    state = read_state(run_directory(run_id) / "state.json")
    published = state.publishedPlatforms or {}
    blogger = published.get("blogger")
    if state.status.value != "published" or blogger is None:
        raise SeoMetaError("Blogger에 발행된 run만 검색 설명을 설정할 수 있습니다.")
    description = check_meta_description(run_id).snippet_preview[:DESCRIPTION_LIMIT].strip()
    if not description:
        raise SeoMetaError("검색 설명 후보가 비어 있습니다. final.md의 '## 요약'을 확인하세요.")
    if not blog_id.isdecimal() or not blogger.postId.isdecimal():
        raise SeoMetaError("Blogger blog/post ID 형식이 올바르지 않습니다.")
    return SeoMetaPlan(run_id=run_id, blog_id=blog_id, post_id=blogger.postId, description=description)


def _description_from_post_body(body: str) -> str:
    """Prefer the summary and fall back to the first prose paragraph in legacy posts."""
    summary = markdown_to_plain(_extract_section(body, "요약"))
    if summary:
        return summary[:DESCRIPTION_LIMIT].strip()

    for paragraph in re.split(r"\n\s*\n", body):
        stripped = paragraph.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        plain = markdown_to_plain(stripped)
        if plain:
            return plain[:DESCRIPTION_LIMIT].strip()
    return ""


def build_all_seo_meta_plans(blog_id: str) -> list[SeoMetaPlan]:
    """Build search-description plans for every published local Blogger post."""
    if not blog_id.isdecimal():
        raise SeoMetaError("Blogger blog ID 형식이 올바르지 않습니다.")

    plans: list[SeoMetaPlan] = []
    for post_path in all_post_paths():
        post = frontmatter.load(post_path)
        if post.metadata.get("status") != "published":
            continue

        slug = post.metadata.get("slug")
        post_id = post.metadata.get("id")
        if not isinstance(slug, str) or not slug:
            raise SeoMetaError(f"{post_path}: slug가 없습니다.")
        if not isinstance(post_id, str) or not post_id.isdecimal():
            raise SeoMetaError(f"{post_path}: Blogger post ID 형식이 올바르지 않습니다.")

        description = _description_from_post_body(post.content)
        if not description:
            raise SeoMetaError(f"{post_path}: 검색 설명 후보가 비어 있습니다. '## 요약'을 확인하세요.")
        plans.append(SeoMetaPlan(slug, blog_id, post_id, description))

    if not plans:
        raise SeoMetaError("검색 설명을 설정할 발행 글이 없습니다.")
    return plans


def _write_plan_record(plan: SeoMetaPlan) -> Path:
    backup_dir = project_root / "temp" / "backups" / "seo-meta"
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"{plan.post_id}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.json"
    path.write_text(
        json.dumps(
            {
                "runId": plan.run_id,
                "blogId": plan.blog_id,
                "postId": plan.post_id,
                "description": plan.description,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _open_search_description(page: Page) -> None:
    textarea = page.locator(
        'textarea[aria-label="검색 설명 입력"], textarea[aria-label="Search description"]'
    )
    if textarea.count() == 0 or not textarea.first.is_visible():
        toggle = page.get_by_text(re.compile(r"^(검색 설명|Search description)$")).first
        toggle.click(timeout=10_000)
    textarea.first.wait_for(state="visible", timeout=10_000)


def _open_editor(page: Page, plan: SeoMetaPlan) -> None:
    page.goto(plan.editor_url, wait_until="domcontentloaded")
    if "accounts.google.com" in page.url:
        print("[seo-meta] 열린 Chrome에서 Google 로그인을 완료해 주세요. 최대 5분 대기합니다.")
        page.wait_for_url(re.compile(r"https://www\.blogger\.com/blog/post/edit/"), timeout=300_000)


def _apply_plan_to_page(page: Page, plan: SeoMetaPlan) -> Path:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    record = _write_plan_record(plan)
    _open_editor(page, plan)
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            _open_search_description(page)
            textarea = page.locator(
                'textarea[aria-label="검색 설명 입력"], textarea[aria-label="Search description"]'
            ).first
            textarea.fill(plan.description)
            page.get_by_role("button", name=re.compile(r"^(업데이트|Update)$")).click(timeout=10_000)
            page.wait_for_timeout(1_500)
            page.reload(wait_until="domcontentloaded")
            _open_search_description(page)
            saved = page.locator(
                'textarea[aria-label="검색 설명 입력"], textarea[aria-label="Search description"]'
            ).first.input_value()
            if saved != plan.description:
                raise SeoMetaError(f"저장 후 값 불일치: {len(saved)}/{len(plan.description)}자")
            return record
        except (PlaywrightError, PlaywrightTimeoutError, SeoMetaError) as error:
            last_error = str(error)
            if attempt < MAX_ATTEMPTS:
                print(f"[seo-meta] {attempt}/{MAX_ATTEMPTS} 실패: {last_error}; 다시 시도합니다.")
                _open_editor(page, plan)
    raise SeoMetaError(f"{MAX_ATTEMPTS}회 실패: {last_error}; 기록: {record}")


def apply_seo_meta(plan: SeoMetaPlan) -> Path:
    from playwright.sync_api import sync_playwright

    profile_dir = project_root / "temp" / "automation_profile"
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            return _apply_plan_to_page(page, plan)
        finally:
            context.close()


def set_seo_meta(run_id: str, blog_id: str, *, dry_run: bool) -> None:
    plan = build_seo_meta_plan(run_id, blog_id)
    print(f"[seo-meta] run={plan.run_id}, post={plan.post_id}, {len(plan.description)}/{DESCRIPTION_LIMIT}자")
    print(f'[seo-meta] "{plan.description}"')
    if dry_run:
        print("[seo-meta] dry-run 완료")
        return
    record = apply_seo_meta(plan)
    print(f"[seo-meta] Blogger 검색 설명 저장 및 재확인 완료; 기록: {record}")


def set_all_seo_meta(blog_id: str, *, dry_run: bool, start_at: int = 1) -> None:
    plans = build_all_seo_meta_plans(blog_id)
    if start_at < 1 or start_at > len(plans):
        raise SeoMetaError(f"--start-at은 1~{len(plans)} 범위여야 합니다.")
    selected_plans = plans[start_at - 1:]
    print(
        f"[seo-meta] 발행 글 {len(plans)}편 중 {start_at}번째부터 "
        f"{len(selected_plans)}편의 Blogger 검색 설명을 준비했습니다."
    )
    if dry_run:
        for plan in selected_plans:
            print(f"[seo-meta] post={plan.post_id}, {len(plan.description)}/{DESCRIPTION_LIMIT}자")
        print("[seo-meta] dry-run 완료")
        return

    from playwright.sync_api import sync_playwright

    profile_dir = project_root / "temp" / "automation_profile"
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            for index, plan in enumerate(selected_plans, start=start_at):
                print(f"[seo-meta] {index}/{len(plans)} post={plan.post_id} 적용 시작")
                try:
                    record = _apply_plan_to_page(page, plan)
                except SeoMetaError as error:
                    raise SeoMetaError(f"{index}/{len(plans)} post={plan.post_id}에서 중단: {error}") from error
                print(f"[seo-meta] {index}/{len(plans)} 저장 및 재확인 완료; 기록: {record}")
        finally:
            context.close()
