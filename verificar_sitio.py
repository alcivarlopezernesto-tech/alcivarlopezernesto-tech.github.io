#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica el sitio generado: enlaces internos, imágenes y metadatos."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DOCS = RAIZ / "docs"


class Recolector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.enlaces: list[str] = []
        self.imagenes: list[str] = []
        self.titulo = ""
        self._en_titulo = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.enlaces.append(str(d["href"]))
        if tag == "img" and d.get("src"):
            self.imagenes.append(str(d["src"]))
        if tag == "title":
            self._en_titulo = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._en_titulo = False

    def handle_data(self, data):
        if self._en_titulo:
            self.titulo += data


def destino(url: str) -> Path | None:
    if url.startswith(("http://", "https://", "mailto:", "tel:", "#")):
        return None
    limpio = url.split("#")[0].split("?")[0]
    if not limpio:
        return None
    if limpio.startswith("/"):
        return DOCS / limpio.lstrip("/")
    return None


def main() -> int:
    if not DOCS.exists():
        print("No existe docs/. Ejecute build.py primero.")
        return 1

    paginas = sorted(DOCS.rglob("*.html"))
    faltantes: list[str] = []
    sin_titulo: list[str] = []

    for pagina in paginas:
        parser = Recolector()
        parser.feed(pagina.read_text(encoding="utf-8", errors="ignore"))
        if not parser.titulo.strip():
            sin_titulo.append(pagina.relative_to(DOCS).as_posix())
        for url in parser.enlaces + parser.imagenes:
            p = destino(url)
            if p is None:
                continue
            if not p.exists():
                faltantes.append(f"{pagina.relative_to(DOCS)} → {url}")

    print(f"Páginas: {len(paginas)}")
    print(f"Enlaces internos rotos: {len(faltantes)}")
    if sin_titulo:
        print(f"Páginas sin <title>: {len(sin_titulo)}")
        for s in sin_titulo:
            print("  ·", s)
    if faltantes:
        print("\nEnlaces rotos:")
        for f in faltantes:
            print("  ·", f)
        return 1
    print("Todos los enlaces internos resuelven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
