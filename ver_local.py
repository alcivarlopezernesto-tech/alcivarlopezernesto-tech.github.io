#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copia el sitio con rutas relativas para abrirlo directo desde el disco."""

import re
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ORIGEN = RAIZ / "docs"
DESTINO_NAME = "vista_local"
DESTINO = RAIZ / DESTINO_NAME


def relativo(url: str, profundidad: int) -> str:
    prefijo = "../" * profundidad
    if url == "/":
        return prefijo + "index.html" if profundidad else "index.html"
    return prefijo + url.lstrip("/")


def procesar(html: str, profundidad: int) -> str:
    def rep(m):
        attr, comillas, url = m.group(1), m.group(2), m.group(3)
        if not url.startswith("/"):
            return m.group(0)
        return f"{attr}={comillas}{relativo(url, profundidad)}{comillas}"

    return re.sub(r'(href|src)=(["\'])(/[^"\']*)\2', rep, html)


def main() -> None:
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    shutil.copytree(ORIGEN, DESTINO)
    total = 0
    for ruta in DESTINO.rglob("*.html"):
        profundidad = len(ruta.relative_to(DESTINO).parts) - 1
        texto = ruta.read_text(encoding="utf-8")
        ruta.write_text(procesar(texto, profundidad), encoding="utf-8")
        total += 1
    print(f"Copia local: {total} páginas en {DESTINO}")
    print(f"Abre: {DESTINO / 'index.html'}")


if __name__ == "__main__":
    main()
