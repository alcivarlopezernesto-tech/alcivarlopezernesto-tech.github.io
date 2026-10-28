#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Control de paridad bilingüe.

Falla si alguna página de contenido/ no tiene su cuerpo en inglés, si le falta
la traducción de un campo visible (sumilla, meta, descripción) o si una etiqueta
de la tabla de datos o de los botones no trae las dos versiones.

Uso: python3 verificar_idiomas.py
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CONTENIDO = ROOT / "contenido"
SEPARADOR = "<!--:en-->"

CAMPOS_CON_PAR = ["sumilla", "meta", "descripcion", "estado", "instrumentacion", "duracion"]


def revisar(ruta: Path):
    fallos = []
    texto = ruta.read_text(encoding="utf-8")
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return [f"{ruta.name}: sin front matter"]
    fm = yaml.safe_load(partes[1]) or {}
    cuerpo = partes[2]

    if SEPARADOR not in cuerpo:
        fallos.append(f"{ruta.name}: falta el cuerpo en inglés ({SEPARADOR})")
    else:
        es, en = cuerpo.split(SEPARADOR, 1)
        if len(en.strip()) < 40:
            fallos.append(f"{ruta.name}: el cuerpo en inglés está vacío o es un marcador")

    for campo in CAMPOS_CON_PAR:
        if campo in fm and not fm.get(f"{campo}_en"):
            fallos.append(f"{ruta.name}: falta {campo}_en")

    for etiqueta, _clave in fm.get("datos") or []:
        if "|" not in str(etiqueta):
            fallos.append(f"{ruta.name}: etiqueta sin versión inglesa: {etiqueta!r}")

    for enlace in fm.get("enlaces") or []:
        if "|" not in str(enlace[0]):
            fallos.append(f"{ruta.name}: botón sin versión inglesa: {enlace[0]!r}")

    return fallos


def main():
    archivos = sorted(CONTENIDO.rglob("*.md"))
    fallos = []
    for ruta in archivos:
        fallos.extend(revisar(ruta))

    print(f"Archivos revisados: {len(archivos)}")
    if fallos:
        print("Páginas incompletas:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("Todas las páginas tienen su versión en inglés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
