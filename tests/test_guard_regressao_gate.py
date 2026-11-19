#!/usr/bin/env python3
"""Guarda contra reversao acidental da logica E0 (PR #591) em validar_fatos.py."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDAR = REPO_ROOT / "validar_fatos.py"
sys.path.insert(0, str(REPO_ROOT))
import validar_fatos as vf  # noqa: E402

_REQUIRED_FUNCS = (
    "regressao_pode_ser_aprovada",
    "regressao_aprovada_json_valido",
    "marca_regressao_em_commits",
    "marca_regressao_detectada",
)
_REGRESSAO_JSON = "_regressao_aprovada.json"


def _ler_validar_fatos() -> str:
    return VALIDAR.read_text(encoding="utf-8-sig")


class GuardRegressaoGateTests(unittest.TestCase):
    def test_modulo_expoe_api_e0_do_pr591(self) -> None:
        for name in _REQUIRED_FUNCS:
            self.assertTrue(
                hasattr(vf, name) and callable(getattr(vf, name)),
                msg=f"validar_fatos perdeu {name!r}",
            )

    def test_regressao_pode_ser_aprovada_exige_json_valido(self) -> None:
        src = _ler_validar_fatos()
        tree = ast.parse(src)
        fn = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "regressao_pode_ser_aprovada"
        )
        body = ast.get_source_segment(src, fn) or ""
        self.assertIn("regressao_aprovada_json_valido", body)
        self.assertIn(_REGRESSAO_JSON, src)

    def test_erros_regressao_nao_dispensa_so_pelo_ultimo_commit(self) -> None:
        src = _ler_validar_fatos()
        fn = next(
            n
            for n in ast.parse(src).body
            if isinstance(n, ast.FunctionDef) and n.name == "erros_regressao"
        )
        body = ast.get_source_segment(src, fn) or ""
        self.assertNotIn(
            'if "[regressao-aprovada]" in msg.lower(): return []',
            body,
            msg="E0 voltou a dispensar regressao apenas pela mensagem do ultimo commit",
        )
        self.assertIn("regressao_pode_ser_aprovada", body)


if __name__ == "__main__":
    unittest.main()