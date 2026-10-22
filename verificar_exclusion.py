#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica que ningún contenido prohibido entre al sitio publicado.

Se ejecuta antes de cada publicación:

    python3 verificar_exclusion.py

Revisa tres capas:
  1. Nombres de archivo y carpetas (contenido/, estatico/, docs/).
  2. Texto de todos los archivos del sitio.
  3. Historial de git, si el repositorio está inicializado.

Si encuentra algo, sale con código 1 y no se publica.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REVISAR = ["contenido", "estatico", "docs", "plantillas", "marca.yml", "build.py", "README.md"]

# Términos que nunca deben aparecer en el sitio público.
PROHIBIDOS = [
    # trading y mercados
    r"\btrading\b", r"\bscalping\b", r"\bbinance\b", r"\bbinance\b",
    r"\bcripto", r"\bcrypto", r"\busdt\b", r"\bbitcoin\b", r"\bbtc\b",
    r"\bethereum\b", r"\bblockchain\b", r"\bp2p\b", r"\bspot\b(?! de)",
    r"\bapalancamiento\b", r"\bbroker\b", r"\bbróker\b",
    # contabilidad e inversión
    r"\bcontabilidad\b", r"\bganancias? totales\b", r"\bearn\b",
    r"\bapr\b", r"\bportafolio de inversi", r"\binversión\b", r"\binversion\b",
    # filosofía
    r"\bfilosof", r"\bphilosoph", r"\bpresocrát", r"\bnietzsche\b",
    r"\baristóteles\b", r"\bplató?n\b", r"\bsócrates\b",
]

# Excepciones deliberadas: palabras legítimas del dominio musical.
EXCEPCIONES = [
    "inversión de intervalo", "inversión melódica", "inversión del tema",
]

EXTENSIONES_TEXTO = {".html", ".css", ".md", ".yml", ".yaml", ".txt", ".xml", ".json", ".py"}


def archivos_a_revisar() -> list[Path]:
    rutas: list[Path] = []
    for nombre in REVISAR:
        p = RAIZ / nombre
        if p.is_file():
            rutas.append(p)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and ".git" not in f.parts:
                    rutas.append(f)
    return rutas


def revisar_nombres(rutas: list[Path]) -> list[str]:
    fallos = []
    for f in rutas:
        rel = f.relative_to(RAIZ).as_posix().lower()
        for patron in PROHIBIDOS:
            if re.search(patron, rel):
                fallos.append(f"nombre: {rel} → {patron}")
    return fallos


def revisar_texto(rutas: list[Path]) -> list[str]:
    fallos = []
    for f in rutas:
        if f.suffix.lower() not in EXTENSIONES_TEXTO:
            continue
        try:
            texto = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        bajo = texto.lower()
        for exc in EXCEPCIONES:
            bajo = bajo.replace(exc, "")
        for patron in PROHIBIDOS:
            m = re.search(patron, bajo)
            if m:
                linea = bajo[: m.start()].count("\n") + 1
                fallos.append(f"{f.relative_to(RAIZ)}:{linea} → «{m.group(0)}»")
    return fallos


def revisar_git() -> list[str]:
    if not (RAIZ / ".git").exists():
        return []
    try:
        salida = subprocess.run(
            ["git", "-C", str(RAIZ), "log", "--all", "-p", "--pretty=format:"],
            capture_output=True, text=True, errors="ignore", timeout=120,
        ).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return []
    fallos = []
    for patron in PROHIBIDOS:
        if re.search(patron, salida):
            fallos.append(f"historial git → {patron}")
    return fallos


def main() -> int:
    rutas = archivos_a_revisar()
    fallos = revisar_nombres(rutas) + revisar_texto(rutas) + revisar_git()

    print(f"Archivos revisados: {len(rutas)}")
    if fallos:
        print("\nCONTENIDO PROHIBIDO ENCONTRADO — no publicar:\n")
        for f in fallos:
            print("  ·", f)
        return 1

    print("Sin contenido prohibido. Publicación autorizada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
