#!/usr/bin/env python3
"""Garante que _frescor.json e arquivos versionados respeitam publicacao_allowlist.txt."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

FORBIDDEN_SUBSTRINGS = ("bak", "backup", "_QSV_", ".manifest", "_temp")
SKIP_PREFIXES = (".github/", "scripts/", "tests/")


def repo_root_from_argv() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return Path(__file__).resolve().parent.parent


def load_allowlist(path: Path) -> set[str]:
    if not path.is_file():
        raise SystemExit(f"Arquivo de allowlist nao encontrado: {path}")
    names: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        names.add(line)
    return names


def git_versioned_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback para ambientes sem git (testes locais montam arvore manualmente).
        return [
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        ]
    return [line for line in out.stdout.splitlines() if line.strip()]


def names_with_forbidden(names: Iterable[str]) -> list[str]:
    bad: list[str] = []
    for name in names:
        if any(sub in name for sub in FORBIDDEN_SUBSTRINGS):
            bad.append(name)
    return sorted(bad)


def main() -> int:
    root = repo_root_from_argv()
    allowlist_path = root / "publicacao_allowlist.txt"
    frescor_path = root / "_frescor.json"

    errors: list[str] = []

    allowlist = load_allowlist(allowlist_path)

    forbidden_allow = names_with_forbidden(allowlist)
    if forbidden_allow:
        errors.append(
            "Nomes proibidos em publicacao_allowlist.txt:\n  "
            + "\n  ".join(forbidden_allow)
        )

    if not frescor_path.is_file():
        errors.append(f"_frescor.json nao encontrado: {frescor_path}")
    else:
        with frescor_path.open(encoding="utf-8-sig") as fh:
            data = json.load(fh)
        arquivos = data.get("arquivos")
        if not isinstance(arquivos, dict):
            errors.append("_frescor.json: chave 'arquivos' ausente ou invalida")
            arquivos = {}

        frescor_keys = set(arquivos.keys())
        fora_allowlist = sorted(frescor_keys - allowlist)
        if fora_allowlist:
            errors.append(
                "_frescor.json contem chaves fora da allowlist:\n  "
                + "\n  ".join(fora_allowlist)
            )

        forbidden_frescor = names_with_forbidden(frescor_keys)
        if forbidden_frescor:
            errors.append(
                "Nomes proibidos em _frescor.json (arquivos):\n  "
                + "\n  ".join(forbidden_frescor)
            )

    versioned = git_versioned_files(root)
    publicados_obrigatorios: list[str] = []
    for rel in versioned:
        if rel.startswith(SKIP_PREFIXES):
            continue
        if rel not in allowlist:
            publicados_obrigatorios.append(rel)
    if publicados_obrigatorios:
        errors.append(
            "Arquivos versionados fora de .github/, scripts/ e tests/ "
            "ausentes da allowlist:\n  "
            + "\n  ".join(sorted(publicados_obrigatorios))
        )

    if errors:
        print("checar_allowlist: FALHA", file=sys.stderr)
        for block in errors:
            print(block, file=sys.stderr)
            print(file=sys.stderr)
        return 1

    print("checar_allowlist: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())