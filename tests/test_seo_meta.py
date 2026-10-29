from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.core.types import PublishedPlatformDetail, RunState, WorkflowStatus
from src.pipeline.seo_check import SeoCheckResult
from src.pipeline.seo_meta import SeoMetaError, SeoMetaPlan, build_all_seo_meta_plans, build_seo_meta_plan, set_all_seo_meta


class SeoMetaTest(unittest.TestCase):
    def test_plan_targets_published_blogger_post_and_limits_description(self) -> None:
        state = RunState(
            runId="20260101000000",
            articleId="article-20260101000000",
            topic="topic",
            status=WorkflowStatus.PUBLISHED,
            humanApproved=True,
            createdAt="2026-01-01T00:00:00Z",
            updatedAt="2026-01-01T00:00:00Z",
            publishedPlatforms={
                "blogger": PublishedPlatformDetail(
                    postId="123",
                    url="https://example.blogspot.com/post",
                    publishedAt="2026-01-01T00:00:00Z",
                )
            },
        )
        preview = "가" * 160
        result = SeoCheckResult(ok=True, snippet_preview=preview, summary_char_count=160)

        with patch("src.pipeline.seo_meta.read_state", return_value=state), patch(
            "src.pipeline.seo_meta.check_meta_description", return_value=result
        ):
            plan = build_seo_meta_plan("20260101000000", "456")

        self.assertEqual(plan.blog_id, "456")
        self.assertEqual(plan.post_id, "123")
        self.assertEqual(plan.description, "가" * 150)

    def test_plan_refuses_unpublished_run(self) -> None:
        state = RunState(
            runId="20260101000000",
            articleId="article-20260101000000",
            topic="topic",
            status=WorkflowStatus.APPROVED,
            humanApproved=True,
            createdAt="2026-01-01T00:00:00Z",
            updatedAt="2026-01-01T00:00:00Z",
        )

        with patch("src.pipeline.seo_meta.read_state", return_value=state), self.assertRaises(SeoMetaError):
            build_seo_meta_plan("20260101000000", "456")

    def test_all_plans_use_published_post_summary_and_frontmatter_id(self) -> None:
        published = SimpleNamespace(
            metadata={"status": "published", "id": "123", "slug": "published-post"},
            content="## 요약\n검색 설명으로 쓸 요약입니다.\n\n## 본문\n내용",
        )
        draft = SimpleNamespace(
            metadata={"status": "draft", "id": "456", "slug": "draft-post"},
            content="## 요약\n초안",
        )

        with patch("src.pipeline.seo_meta.all_post_paths", return_value=[Path("published.md"), Path("draft.md")]), patch(
            "src.pipeline.seo_meta.frontmatter.load", side_effect=[published, draft]
        ):
            plans = build_all_seo_meta_plans("789")

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].run_id, "published-post")
        self.assertEqual(plans[0].post_id, "123")
        self.assertEqual(plans[0].description, "검색 설명으로 쓸 요약입니다.")

    def test_all_plans_fall_back_to_intro_when_summary_is_missing(self) -> None:
        published = SimpleNamespace(
            metadata={"status": "published", "id": "123", "slug": "published-post"},
            content="# 제목\n\n첫 문단을 검색 설명으로 사용합니다.\n\n## 본문\n내용",
        )

        with patch("src.pipeline.seo_meta.all_post_paths", return_value=[Path("published.md")]), patch(
            "src.pipeline.seo_meta.frontmatter.load", return_value=published
        ):
            plans = build_all_seo_meta_plans("789")

        self.assertEqual(plans[0].description, "첫 문단을 검색 설명으로 사용합니다.")

    def test_all_dry_run_resumes_from_requested_position(self) -> None:
        plans = [
            SeoMetaPlan("first", "789", "111", "첫 번째"),
            SeoMetaPlan("second", "789", "222", "두 번째"),
        ]

        with patch("src.pipeline.seo_meta.build_all_seo_meta_plans", return_value=plans), patch("builtins.print") as output:
            set_all_seo_meta("789", dry_run=True, start_at=2)

        rendered = "\n".join(str(call.args[0]) for call in output.call_args_list)
        self.assertNotIn("post=111", rendered)
        self.assertIn("post=222", rendered)


if __name__ == "__main__":
    unittest.main()
