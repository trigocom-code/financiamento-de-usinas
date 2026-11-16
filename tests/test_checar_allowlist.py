#!/usr/bin/env python3
"""Testes do gate de allowlist de publicacao."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "checar_allowlist.py"


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        capture_output=True,
        text=True,
    )


def git_add_all(root: Path, *paths: str) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", *paths], cwd=root, check=True)


class ChecarAllowlistTests(unittest.TestCase):
    def test_passa_no_estado_corrigido_do_repositorio(self) -> None:
        result = run_checker(REPO_ROOT)
        self.assertEqual(
            result.returncode,
            0,
            msg=result.stdout + result.stderr,
        )
        self.assertIn("OK", result.stdout)

    def test_falha_quando_frescor_tem_chave_fora_da_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "publicacao_allowlist.txt").write_text(
                "index.html\npublicacao_allowlist.txt\n_frescor.json\n",
                encoding="utf-8",
            )
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            frescor = {
                "_meta": {"gerado_em": "2026-01-01T00:00:00-03:00"},
                "arquivos": {
                    "index.html": "2026-01-01T00:00:00-03:00",
                    "secreto.html": "2026-01-01T00:00:00-03:00",
                },
            }
            (root / "_frescor.json").write_text(
                json.dumps(frescor, indent=2), encoding="utf-8"
            )
            git_add_all(
                root,
                "index.html",
                "publicacao_allowlist.txt",
                "_frescor.json",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("fora da allowlist", result.stderr)
            self.assertIn("secreto.html", result.stderr)

    def test_falha_quando_arquivo_versionado_nao_esta_na_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "publicacao_allowlist.txt").write_text(
                "index.html\npublicacao_allowlist.txt\n_frescor.json\n",
                encoding="utf-8",
            )
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "extra.html").write_text("<html></html>", encoding="utf-8")
            frescor = {
                "_meta": {},
                "arquivos": {"index.html": "2026-01-01T00:00:00-03:00"},
            }
            (root / "_frescor.json").write_text(
                json.dumps(frescor), encoding="utf-8"
            )
            git_add_all(
                root,
                "index.html",
                "extra.html",
                "publicacao_allowlist.txt",
                "_frescor.json",
            )
            result = run_checker(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ausentes da allowlist", result.stderr)
            self.assertIn("extra.html", result.stderr)

    def test_falha_quando_nome_proibido_em_frescor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = "_bak_index_2026.html"
            (root / "publicacao_allowlist.txt").write_text(
                f"{bad}\npublicacao_allowlist.txt\n_frescor.json\n",
                encoding="utf-8",
            )
            frescor = {
                "_meta": {},
                "arquivos": {bad: "2026-01-01T00:00:00-03:00"},
            }
            (root / "_frescor.json").write_text(
                json.dumps(frescor), encoding="utf-8"
            )
            git_add_all(root, "publicacao_allowlist.txt", "_frescor.json")
            result = run_checker(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Nomes proibidos", result.stderr)
            self.assertIn(bad, result.stderr)


if __name__ == "__main__":
    unittest.main()