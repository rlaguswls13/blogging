import unittest

from src.pipeline.converter import linkify_markdown


class LinkifyTest(unittest.TestCase):
    def test_bare_url_is_wrapped(self):
        self.assertEqual(linkify_markdown("see https://a.io/x now"), "see <https://a.io/x> now")

    def test_inline_code_span_is_left_alone(self):
        text = "redirect `http://localhost:8080/cb` then https://a.io/x"
        self.assertEqual(linkify_markdown(text), "redirect `http://localhost:8080/cb` then <https://a.io/x>")

    def test_fenced_code_and_existing_links_are_left_alone(self):
        text = "```\nhttps://a.io\n```\n[t](https://b.io)"
        self.assertEqual(linkify_markdown(text), text)


if __name__ == "__main__":
    unittest.main()
