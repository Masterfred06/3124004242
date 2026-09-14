"""Unit tests for the plagiarism checker."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from plagiarism_checker import (
    DocumentError,
    calculate_similarity,
    check_documents,
    extract_document_text,
    normalize_text,
    read_text_file,
    run_cli,
    write_answer,
)


class PlagiarismCheckerTests(unittest.TestCase):
    def test_identical_text_has_full_similarity(self) -> None:
        self.assertAlmostEqual(calculate_similarity("今天天气很好", "今天天气很好"), 1.0)

    def test_empty_documents_are_equal(self) -> None:
        self.assertAlmostEqual(calculate_similarity("", ""), 1.0)

    def test_one_empty_document_has_zero_similarity(self) -> None:
        self.assertAlmostEqual(calculate_similarity("今天天气很好", ""), 0.0)

    def test_normalize_text_removes_punctuation_and_spaces(self) -> None:
        self.assertEqual(normalize_text("Ａ B，今 天！"), "ab今天")

    def test_modified_example_keeps_medium_similarity(self) -> None:
        original = "今天是星期天，天气晴，今天晚上我要去看电影。"
        suspect = "今天是周天，天气晴朗，我晚上要去看电影。"
        self.assertGreater(calculate_similarity(original, suspect), 0.60)

    def test_unrelated_text_has_low_similarity(self) -> None:
        original = "今天是星期天，天气晴，今天晚上我要去看电影。"
        suspect = "计算机网络课程需要完成套接字通信实验。"
        self.assertLess(calculate_similarity(original, suspect), 0.30)

    def test_plain_html_visible_text_is_extracted(self) -> None:
        html = "<html><body><p>正文一</p><script>bad()</script><p>正文二</p></body></html>"
        self.assertIn("正文一", extract_document_text(html))
        self.assertIn("正文二", extract_document_text(html))
        self.assertNotIn("bad", extract_document_text(html))

    def test_github_blob_html_prefers_code_lines(self) -> None:
        html = (
            "<html><body><nav>GitHub</nav><table>"
            '<td id="LC1" class="blob-code js-file-line">第一行</td>'
            '<td id="LC2" class="blob-code js-file-line">第二行</td>'
            "</table></body></html>"
        )
        self.assertEqual(extract_document_text(html).strip(), "第一行\n第二行")

    def test_check_documents_reads_utf8_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original = Path(temp_dir) / "original.txt"
            suspect = Path(temp_dir) / "suspect.txt"
            original.write_text("今天晚上我要去看电影", encoding="utf-8")
            suspect.write_text("今天晚上我要去看电影", encoding="utf-8")
            self.assertAlmostEqual(check_documents(str(original), str(suspect)), 1.0)

    def test_read_text_file_reports_missing_file(self) -> None:
        with self.assertRaises(DocumentError):
            read_text_file("not_exists.txt")

    def test_write_answer_uses_two_decimal_places(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            answer = Path(temp_dir) / "answer.txt"
            write_answer(str(answer), 0.836)
            self.assertEqual(answer.read_text(encoding="utf-8"), "0.84")

    def test_run_cli_writes_answer_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original = Path(temp_dir) / "original.txt"
            suspect = Path(temp_dir) / "suspect.txt"
            answer = Path(temp_dir) / "answer.txt"
            original.write_text("今天晚上我要去看电影", encoding="utf-8")
            suspect.write_text("今天晚上我要去看电影", encoding="utf-8")

            exit_code = run_cli([str(original), str(suspect), str(answer)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(answer.read_text(encoding="utf-8"), "1.00")

    def test_run_cli_rejects_wrong_argument_count(self) -> None:
        with redirect_stderr(StringIO()):
            self.assertEqual(run_cli([]), 2)

    def test_sample_add_file_stays_in_expected_range(self) -> None:
        sample_dir = Path(__file__).resolve().parents[1] / "测试文本"
        score = check_documents(
            str(sample_dir / "orig.txt"), str(sample_dir / "orig_0.8_add.txt")
        )
        self.assertGreater(score, 0.80)
        self.assertLess(score, 0.95)

    def test_sample_html_file_extracts_article_content(self) -> None:
        sample_dir = Path(__file__).resolve().parents[1] / "测试文本"
        score = check_documents(
            str(sample_dir / "orig.txt"), str(sample_dir / "orig_0.8_dis_1.txt")
        )
        self.assertGreater(score, 0.90)


if __name__ == "__main__":
    unittest.main()
