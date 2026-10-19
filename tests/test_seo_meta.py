from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.core.types import PublishedPlatformDetail, RunState, WorkflowStatus
from src.pipeline.seo_check import SeoCheckResult
from src.pipeline.seo_meta import SeoMetaError, build_seo_meta_plan


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


if __name__ == "__main__":
    unittest.main()
