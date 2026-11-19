#!/usr/bin/env python3
"""Testes do E0 anti-regressao em cenarios de push e pull_request (merge sintetico)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import validar_fatos as vf  # noqa: E402

FATOS = "Fatos_Exemplo_Folder_SOA.json"
REGRESSAO_JSON = "_regressao_aprovada.json"


def _run_git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, stderr=subprocess.DEVNULL, text=True
    ).strip()


def _write_fatos(root: Path, n: int) -> None:
    doc = {
        "_meta": {
            "schema_version": "1.0",
            "verificado_em": "2026-11-18",
            "regra_fonte_associacao": "teste",
        },
        "fatos": [{"fato_id": f"f{i}", "valor": "x", "tema": "t", "norma": "n"} for i in range(n)],
    }
    (root / FATOS).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def _write_regressao_json(root: Path) -> None:
    (root / REGRESSAO_JSON).write_text(
        json.dumps({"_meta": {"aprovado_em": "2026-11-18"}}, ensure_ascii=False),
        encoding="utf-8",
    )


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)


class ErrosRegressaoTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)

    def _clear_pr_env(self) -> None:
        for k in ("GITHUB_HEAD_SHA", "GITHUB_BASE_SHA", "PR_TITLE", "PR_BODY"):
            os.environ.pop(k, None)

    def test_pr_merge_sem_marca_head_com_marca_e_sinal_valido_passa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            _write_fatos(root, 8)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)
            base_sha = _run_git(root, "rev-parse", "HEAD")

            _write_fatos(root, 3)
            _write_regressao_json(root)
            subprocess.run(["git", "add", FATOS, REGRESSAO_JSON], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "monitores [regressao-aprovada] reducao de fatos",
                ],
                cwd=root,
                check=True,
            )
            head_sha = _run_git(root, "rev-parse", "HEAD")

            subprocess.run(["git", "checkout", "-q", base_sha], cwd=root, check=True)
            subprocess.run(
                ["git", "merge", "--no-ff", "-q", "-m", "Merge pull request (sintetico)", head_sha],
                cwd=root,
                check=True,
            )

            self._clear_pr_env()
            os.environ["GITHUB_BASE_SHA"] = base_sha
            os.environ["GITHUB_HEAD_SHA"] = head_sha

            erros = vf.erros_regressao(str(root))
            self.assertEqual(erros, [])

    def test_sem_marca_em_lugar_algum_barra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            _write_fatos(root, 8)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)

            _write_fatos(root, 3)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "queda sem aprovacao"], cwd=root, check=True)

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertTrue(erros)
            self.assertTrue(any("REGRESSAO qtde" in x for x in erros))

    def test_marca_sem_regressao_json_barra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            _write_fatos(root, 8)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)

            _write_fatos(root, 3)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "monitores [regressao-aprovada]"],
                cwd=root,
                check=True,
            )

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertTrue(erros)
            self.assertTrue(any(REGRESSAO_JSON in x for x in erros))

    def test_commit_com_marca_meta_sem_queda_de_fatos_passa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            _write_fatos(root, 5)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)
            (root / "notas.txt").write_text("doc", encoding="utf-8")
            subprocess.run(["git", "add", "notas.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "docs sobre [regressao-aprovada] no gate"],
                cwd=root,
                check=True,
            )
            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertEqual(erros, [])

    def test_titulo_pr_com_marca_sem_json_nao_dispensa_regressao(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            _write_fatos(root, 8)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)
            _write_fatos(root, 3)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "queda"], cwd=root, check=True)
            self._clear_pr_env()
            os.environ["PR_TITLE"] = "pub [regressao-aprovada] sem json"
            erros = vf.erros_regressao(str(root))
            self.assertTrue(any("REGRESSAO qtde" in x for x in erros))
            self.assertFalse(any(REGRESSAO_JSON in x for x in erros))

    def test_push_ultimo_commit_com_marca_e_sinal_valido_passa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            _write_fatos(root, 8)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)

            _write_fatos(root, 5)
            _write_regressao_json(root)
            subprocess.run(["git", "add", FATOS, REGRESSAO_JSON], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-q",
                    "-m",
                    "atualiza fatos [regressao-aprovada]",
                ],
                cwd=root,
                check=True,
            )

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertEqual(erros, [])


if __name__ == "__main__":
    unittest.main()