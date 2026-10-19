import unittest

from src.tools.check_code_blocks import check_bash_syntax, check_logic_match, extract_claimed_identifiers
from src.tools.check_opinion_insight import check_claim_evidence_alignment


class BashSyntaxTest(unittest.TestCase):
    def test_valid_script_passes_regardless_of_temp_path_style(self):
        self.assertIsNone(check_bash_syntax("echo hi\nls -la\n"))

    def test_real_syntax_error_is_reported(self):
        self.assertIsNotNone(check_bash_syntax("if true; then\necho hi\n"))


class LogicMatchFalsePositiveTest(unittest.TestCase):
    def test_config_file_package_and_glob_quotes_are_not_identifiers(self):
        context = "`application.yml`에서 `google-api-python-client`와 `spring.datasource.hikari.*`를 설정한다."
        self.assertEqual(extract_claimed_identifiers(context), [])

    def test_real_identifier_is_still_checked(self):
        _claimed, missing = check_logic_match("print('x')", "`hashCode()`를 호출한다.", "java")
        self.assertEqual(missing, ["hashCode()"])

    def test_output_blocks_are_skipped_but_source_blocks_are_not(self):
        context = "`a.speak()` 호출 결과는 다음과 같다."
        self.assertEqual(check_logic_match("Woof", context, ""), ([], []))
        self.assertEqual(check_logic_match("Woof", context, "text"), ([], []))
        _claimed, missing = check_logic_match("Woof", context, "java")
        self.assertEqual(missing, ["a.speak()"])


class ClaimAlignmentTest(unittest.TestCase):
    def test_template_comment_examples_are_not_claims(self):
        diff = "<!--\n예: 직접 돌려본 벤치마크 수치, 실측\n-->\n실제 내용만 있다."
        self.assertEqual(check_claim_evidence_alignment(diff, "본문"), [])

    def test_real_unsupported_claim_is_still_flagged(self):
        self.assertEqual(check_claim_evidence_alignment("벤치마크를 돌려봤다", "수치 없음"), [("벤치마크", False)])


if __name__ == "__main__":
    unittest.main()
