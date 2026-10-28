#!/usr/bin/env python3
import re, shutil, subprocess, datetime
from pathlib import Path

S = Path(__file__).resolve().parent
PED = S.parent / "cadenza_pedagogy" / "content"
MD = S / "contenido" / "pedagogia" / "creacion-y-arreglos.md"
PDFS = S / "estatico" / "pdf" / "guias"

MES = ["septiembre", "octubre", "noviembre", "diciembre", "enero",
       "febrero", "marzo", "abril", "mayo", "junio"]
MESE = ["September", "October", "November", "December", "January",
        "February", "March", "April", "May", "June"]

def pdf_origen(nivel, mes):
    dirs = {1: "creacion_i", 2: "creacion_ii"}
    p = PED / dirs[nivel] / "2026-2027" / "guias" / f"guia_metodologica_{dirs[nivel]}_{mes}_2026-2027.pdf"
    return p

def destino(nivel, mes):
    return PDFS / f"guia-creacion-{nivel}-{mes}-2026-2027.pdf"

def fila(nivel, mes):
    i = MES.index(mes)
    ruta = f"guias/guia-creacion-{nivel}-{mes}-2026-2027.pdf"
    return f'      - ["{MES[i].capitalize()}|{MESE[i]}", "{ruta}", 3]'

def insertar(texto, nivel, mes):
    marca = "Guías metodológicas, Creación y Arreglos " + ("I|" if nivel == 1 else "II|")
    pos = texto.index(marca)
    fin = texto.index("---", pos)
    bloque = texto[pos:fin]
    lineas = bloque.splitlines()
    ultimo = max(i for i, l in enumerate(lineas) if l.startswith('      - ["'))
    lineas.insert(ultimo + 1, fila(nivel, mes))
    return texto[:pos] + "\n".join(lineas) + "\n" + texto[fin:]

def meses_hasta_hoy():
    hoy = datetime.date.today()
    if hoy.year != 2026 and hoy.month > 8:
        return []
    if hoy.month in (7, 8):
        return []
    fin = hoy.month
    orden = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
    anio_ini = 9
    salida = []
    for n in orden:
        salida.append(n)
        if n == fin:
            break
    return [MES[orden.index(n)] for n in salida]

def main():
    texto = MD.read_text(encoding="utf-8")
    publicados, faltan = [], []
    for mes in meses_hasta_hoy():
        for nivel in (1, 2):
            origen = pdf_origen(nivel, mes)
            if not origen.exists():
                faltan.append(f"{nivel}-{mes}")
                continue
            destino(nivel, mes).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen, destino(nivel, mes))
            if f"guia-creacion-{nivel}-{mes}-" not in texto:
                texto = insertar(texto, nivel, mes)
                publicados.append(f"Creación {nivel} — {mes}")
    MD.write_text(texto, encoding="utf-8")
    return publicados, faltan

if __name__ == "__main__":
    pub, fal = main()
    if not pub and not fal:
        print("Sin novedades: no corresponde publicar guías este mes.")
        raise SystemExit(0)
    for c in ("python3 build.py", "python3 verificar_sitio.py", "python3 verificar_idiomas.py", "python3 ver_local.py"):
        r = subprocess.run(c.split(), cwd=S, capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            print("FALLO en", c, r.stdout[-400:], r.stderr[-400:])
            raise SystemExit(1)
    if pub:
        subprocess.run(["git", "add", "-A"], cwd=S)
        subprocess.run(["git", "commit", "-q", "-m", "Publicar guías: " + ", ".join(pub)], cwd=S)
    print("Publicadas:", ", ".join(pub) if pub else "ninguna")
    print("Sin PDF todavía:", ", ".join(fal) if fal else "ninguna")
