#!/usr/bin/env python3
"""Gate: selo do catálogo usa _meta.verificado_em, não hora de gravação/commit."""

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "Catalogo_Vivos_SOA.html"

FORBIDDEN = (
    "_frescor.json",
    "api.github.com",
    "/commits",
    "lastModified",
    "Last-Modified",
    "LastWriteTime",
)

SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL | re.IGNORECASE)


def extract_inline_script(html: str) -> str:
    scripts = SCRIPT_RE.findall(html)
    if not scripts:
        raise AssertionError("nenhum <script> inline encontrado em Catalogo_Vivos_SOA.html")
    # último bloco é o selo de frescor
    return scripts[-1]


class TestSeloDataConferencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML.read_text(encoding="utf-8")
        cls.script = extract_inline_script(cls.html)

    def test_nao_usa_fontes_de_hora_de_gravacao(self):
        lower = self.script.lower()
        hits = [tok for tok in FORBIDDEN if tok.lower() in lower]
        self.assertEqual(
            hits,
            [],
            f"script do selo ainda referencia fonte proibida: {hits}",
        )

    def test_le_verificado_em_na_fonte(self):
        self.assertIn("verificado_em", self.script)
        self.assertIn("_meta", self.script)

    def test_texto_sem_data_de_conferencia(self):
        self.assertIn("sem data de conferência", self.script)
        self.assertIn("sem data de conferência", self.html)


if __name__ == "__main__":
    if not HTML.is_file():
        print(f"arquivo ausente: {HTML}", file=sys.stderr)
        sys.exit(2)
    unittest.main()