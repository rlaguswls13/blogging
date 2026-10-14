from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.pipeline.patch_urls import PatchError, UrlEdit, patch_urls, replace_destinations


class PatchUrlsTest(unittest.TestCase):
    def test_only_href_destination_changes(self) -> None:
        edit = UrlEdit(before="https://old.test/a", after="https://new.test/a?x=1&y=2")
        source = '<a class="x" href="https://old.test/a">https://old.test/a</a>\r\n'
        result = replace_destinations(source, [edit], live=True)
        self.assertEqual(result, '<a class="x" href="https://new.test/a?x=1&amp;y=2">https://old.test/a</a>\r\n')

    def test_already_updated_markdown_preserves_bytes(self) -> None:
        source = "[label](https://new.test/a)\r\n"
        result = replace_destinations(source, [UrlEdit(before="https://old.test/a", after="https://new.test/a")], live=False)
        self.assertEqual(result, source)

    def test_missing_or_ambiguous_destination_refuses(self) -> None:
        edit = UrlEdit(before="https://old.test/a", after="https://new.test/a")
        for source in ("plain text", '<a href="https://old.test/a"></a><a href="https://old.test/a"></a>'):
            with self.subTest(source=source), self.assertRaises(PatchError):
                replace_destinations(source, [edit], live=True)

    def test_invalid_local_plan_never_opens_blogger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            article = root / "post.md"
            article.write_text("---\nid: '123'\nstatus: published\n---\nno links", encoding="utf-8")
            edits = root / "edits.json"
            edits.write_text('[{"before":"https://old.test/a","after":"https://new.test/a"}]', encoding="utf-8")
            with patch("src.pipeline.patch_urls.find_post_by_slug", return_value=article), patch("src.pipeline.patch_urls.BloggerPublisher") as publisher:
                with self.assertRaises(PatchError):
                    patch_urls("post", edits)
                publisher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
