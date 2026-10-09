from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src" / "tools" / "build_session_backlink_index.py"


def run_builder(vault_root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ | {
        "PROJECT_RAG_PATH": str(vault_root),
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
    )


class BuildSessionBacklinkIndexTest(unittest.TestCase):
    def test_builder_preserves_the_previous_index_when_temporary_output_cannot_be_written(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault_root = Path(temporary_directory) / "atomic-vault"
            raw_dir = vault_root / "ai-blogging" / "sessions" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "2026-08-20.md").write_text(
                "### 세션 기록 (2026-08-20 12:00:00)\nmain.py\n",
                encoding="utf-8",
            )
            index_path = vault_root / "ai-blogging" / "sessions" / "raw-index.json"
            previous_bytes = b"previous index bytes"
            index_path.write_bytes(previous_bytes)
            temporary_index_path = index_path.with_suffix(f"{index_path.suffix}.tmp")
            temporary_index_path.mkdir()

            failed_write = run_builder(vault_root)

            self.assertEqual(failed_write.returncode, 1)
            self.assertEqual(index_path.read_bytes(), previous_bytes)

            temporary_index_path.rmdir()
            resumed_write = run_builder(vault_root)

            self.assertEqual(resumed_write.returncode, 0, resumed_write.stderr)
            self.assertNotEqual(index_path.read_bytes(), previous_bytes)
            self.assertFalse(temporary_index_path.exists())

    def test_builder_rejects_a_missing_raw_sessions_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault_root = Path(temporary_directory) / "missing-vault"
            result = run_builder(vault_root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("없음", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse((vault_root / "ai-blogging" / "sessions" / "raw-index.json").exists())

    def test_builder_rejects_raw_files_without_session_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault_root = Path(temporary_directory) / "malformed-vault"
            raw_dir = vault_root / "ai-blogging" / "sessions" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "broken.md").write_text("not a session block", encoding="utf-8")

            result = run_builder(vault_root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("세션 블록", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse((vault_root / "ai-blogging" / "sessions" / "raw-index.json").exists())

    def test_builder_is_deterministic_for_an_external_project_rag_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault_root = Path(temporary_directory) / "external-vault"
            raw_dir = vault_root / "ai-blogging" / "sessions" / "raw"
            raw_dir.mkdir(parents=True)
            raw_path = raw_dir / "2026-08-20.md"
            raw_path.write_text(
                "# 세션 기록 — 2026-08-20\n\n"
                "### 세션 기록 (2026-08-20 12:00:00)\n"
                "main.py와 validate.py를 검토했습니다.\n",
                encoding="utf-8",
            )
            index_path = vault_root / "ai-blogging" / "sessions" / "raw-index.json"

            first = run_builder(vault_root)
            first_bytes = index_path.read_bytes()
            second = run_builder(vault_root)
            second_bytes = index_path.read_bytes()

            self.assertEqual(
                (first.returncode, second.returncode),
                (0, 0),
                f"first stderr: {first.stderr}\n"
                f"second stderr: {second.stderr}\n"
                f"first SHA256: {hashlib.sha256(first_bytes).hexdigest()}\n"
                f"second SHA256: {hashlib.sha256(second_bytes).hexdigest()}",
            )
            self.assertIn(f"완료: {index_path.resolve()} 생성/갱신.", first.stdout)
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(hashlib.sha256(first_bytes).digest(), hashlib.sha256(second_bytes).digest())

            index = json.loads(second_bytes)
            self.assertEqual(index["version"], "1.0.0")
            self.assertEqual(index["generatedAt"], "2026-08-20T00:00:00Z")
            self.assertEqual(index["files"][raw_path.name]["totalLines"], 4)
            self.assertEqual(index["tagIndex"]["pipeline-quality"][0]["file"], raw_path.name)

            raw_path.write_text(
                raw_path.read_text(encoding="utf-8")
                + "\n### 세션 기록 (2026-08-21 12:00:00)\n"
                + "theme widget를 검토했습니다.\n",
                encoding="utf-8",
            )
            changed = run_builder(vault_root)
            changed_bytes = index_path.read_bytes()

            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertNotEqual(changed_bytes, second_bytes)
            self.assertEqual(json.loads(changed_bytes)["generatedAt"], "2026-08-21T00:00:00Z")
