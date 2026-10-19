from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Final

from src.core.files import read_state
from src.core.paths import project_root, run_directory
from src.pipeline.seo_check import check_meta_description


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


def apply_seo_meta(plan: SeoMetaPlan) -> Path:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    record = _write_plan_record(plan)
    profile_dir = project_root / "temp" / "automation_profile"
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(plan.editor_url, wait_until="domcontentloaded")
            if "accounts.google.com" in page.url:
                print("[seo-meta] 열린 Chrome에서 Google 로그인을 완료해 주세요. 최대 5분 대기합니다.")
                page.wait_for_url(re.compile(r"https://www\.blogger\.com/blog/post/edit/"), timeout=300_000)

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
                        page.goto(plan.editor_url, wait_until="domcontentloaded")
            raise SeoMetaError(f"{MAX_ATTEMPTS}회 실패: {last_error}; 기록: {record}")
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
