#!/usr/bin/env python3
"""E0: dispensa de regressao exige diff no JSON, por_arquivo e contagem_depois."""

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
MARCA_COMMIT = "queda [regressao-aprovada] intencional"


def _run_git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, stderr=subprocess.DEVNULL, text=True
    ).strip()


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)


def _write_fatos(root: Path, n: int) -> None:
    doc = {
        "_meta": {
            "schema_version": "1.0",
            "verificado_em": "2026-11-18",
            "regra_fonte_associacao": "teste",
        },
        "fatos": [
            {"fato_id": f"f{i}", "valor": "x", "tema": "t", "norma": "n"}
            for i in range(n)
        ],
    }
    (root / FATOS).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def _write_regressao(
    root: Path,
    *,
    por_arquivo: dict,
    meta: dict | None = None,
) -> None:
    doc = {
        "_meta": meta or {"data": "2026-11-20", "motivo": "teste unitario"},
        "por_arquivo": por_arquivo,
    }
    (root / REGRESSAO_JSON).write_text(
        json.dumps(doc, ensure_ascii=False),
        encoding="utf-8",
    )


class RegressaoAprovadaDispensaTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)

    def _clear_pr_env(self) -> None:
        for k in ("GITHUB_HEAD_SHA", "GITHUB_BASE_SHA", "PR_TITLE", "PR_BODY"):
            os.environ.pop(k, None)

    def _commit_base(self, root: Path, n: int = 8) -> str:
        _write_fatos(root, n)
        subprocess.run(["git", "add", FATOS], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)
        return _run_git(root, "rev-parse", "HEAD")

    def test_json_antigo_na_base_com_marca_ainda_barra(self) -> None:
        """Aprovacao ja na main, sem alterar no PR, nao dispensa nova regressao."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            _write_regressao(
                root,
                por_arquivo={
                    FATOS: {"contagem_antes": 99, "contagem_depois": 3, "itens": []}
                },
            )
            subprocess.run(["git", "add", REGRESSAO_JSON], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "json legado na main"], cwd=root, check=True)
            self._commit_base(root, 8)

            _write_fatos(root, 3)
            subprocess.run(["git", "add", FATOS], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", MARCA_COMMIT], cwd=root, check=True)

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertTrue(any("REGRESSAO qtde" in x for x in erros))

    def test_json_tocado_sem_arquivo_regredido_na_lista_barra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._commit_base(root, 8)

            _write_fatos(root, 4)
            _write_regressao(
                root,
                por_arquivo={
                    "Fatos_Outro_Folder_SOA.json": {
                        "contagem_antes": 8,
                        "contagem_depois": 4,
                        "itens": [],
                    }
                },
            )
            subprocess.run(["git", "add", FATOS, REGRESSAO_JSON], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", MARCA_COMMIT], cwd=root, check=True)

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertTrue(any("REGRESSAO qtde" in x for x in erros))

    def test_contagem_depois_divergente_barra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._commit_base(root, 8)

            _write_fatos(root, 4)
            _write_regressao(
                root,
                por_arquivo={
                    FATOS: {"contagem_antes": 8, "contagem_depois": 99, "itens": []}
                },
            )
            subprocess.run(["git", "add", FATOS, REGRESSAO_JSON], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", MARCA_COMMIT], cwd=root, check=True)

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertTrue(any("REGRESSAO qtde" in x for x in erros))

    def test_json_tocado_arquivo_listado_contagem_ok_e_marca_aprova(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._commit_base(root, 8)

            _write_fatos(root, 4)
            _write_regressao(
                root,
                por_arquivo={
                    FATOS: {"contagem_antes": 8, "contagem_depois": 4, "itens": []}
                },
            )
            subprocess.run(["git", "add", FATOS, REGRESSAO_JSON], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", MARCA_COMMIT], cwd=root, check=True)

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertEqual(erros, [])

    def test_sem_marca_barra_mesmo_com_json_correto(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._commit_base(root, 8)

            _write_fatos(root, 4)
            _write_regressao(
                root,
                por_arquivo={
                    FATOS: {"contagem_antes": 8, "contagem_depois": 4, "itens": []}
                },
            )
            subprocess.run(["git", "add", FATOS, REGRESSAO_JSON], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "queda sem marca no commit"],
                cwd=root,
                check=True,
            )

            self._clear_pr_env()
            erros = vf.erros_regressao(str(root))
            self.assertTrue(any("REGRESSAO qtde" in x for x in erros))


if __name__ == "__main__":
    unittest.main()