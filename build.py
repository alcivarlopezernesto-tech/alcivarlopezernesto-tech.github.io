#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generador del sitio de Cadenza Inc.

Lee los archivos Markdown de contenido/ y produce el sitio estático en docs/,
que es la carpeta que GitHub Pages publica (rama main, carpeta /docs).

No requiere dependencias externas salvo PyYAML y Markdown.
"""

from __future__ import annotations

import html
import shutil
from pathlib import Path
from string import Template

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
CONTENIDO = ROOT / "contenido"
PLANTILLAS = ROOT / "plantillas"
ESTATICO = ROOT / "estatico"
SALIDA = ROOT / "docs"

MARCA = yaml.safe_load((ROOT / "marca.yml").read_text(encoding="utf-8"))
NAV = MARCA["navegacion"]
SITIO = MARCA["sitio"]

MD = markdown.Markdown(extensions=["extra", "tables", "attr_list", "md_in_html"])


def leer_ficha(ruta: Path) -> dict:
    """Separa front matter YAML del cuerpo Markdown."""
    texto = ruta.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        raise ValueError(f"Sin front matter: {ruta}")
    _, fm, cuerpo = texto.split("---", 2)
    datos = yaml.safe_load(fm) or {}
    datos["_cuerpo"] = cuerpo.strip()
    datos["_slug"] = datos.get("slug") or ruta.stem
    datos["_ruta"] = ruta
    return datos


def coleccion(nombre: str) -> list[dict]:
    carpeta = CONTENIDO / nombre
    if not carpeta.exists():
        return []
    fichas = [leer_ficha(p) for p in sorted(carpeta.glob("*.md"))]
    orden = {"obras": "anio", "pedagogia": "orden", "investigacion": "orden", "servicios": "orden"}
    clave = orden.get(nombre, "titulo")
    return sorted(fichas, key=lambda f: (f.get(clave) is None, f.get(clave), f.get("titulo", "")))


def md(texto: str) -> str:
    MD.reset()
    return MD.convert(texto)


def nav_html(activo: str) -> str:
    partes = []
    for item in NAV:
        clase = ' class="activo"' if item["url"].strip("/") == activo.strip("/") else ""
        partes.append(f'<a href="{item["url"]}"{clase}>{html.escape(item["titulo"])}</a>')
    return "\n      ".join(partes)


def pagina(destino: Path, titulo: str, cuerpo: str, activo: str = "",
           descripcion: str | None = None, clase: str = "") -> None:
    plantilla = Template((PLANTILLAS / "base.html").read_text(encoding="utf-8"))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        plantilla.substitute(
            titulo=titulo,
            titulo_sitio=SITIO["nombre"],
            descripcion=html.escape(descripcion or SITIO["descripcion"]),
            cuerpo=cuerpo,
            nav=nav_html(activo),
            lema=SITIO["lema"],
            correo=SITIO["correo"],
            anio=SITIO["anio"],
            clase=clase,
        ),
        encoding="utf-8",
    )


def tarjeta(ficha: dict, base: str) -> str:
    meta = ficha.get("meta") or ficha.get("resumen") or ""
    return f"""<a class="tarjeta" href="/{base}/{ficha['_slug']}.html">
  <span class="tarjeta-meta">{html.escape(str(meta))}</span>
  <h3>{html.escape(ficha['titulo'])}</h3>
  <p>{html.escape(ficha.get('sumilla', ''))}</p>
</a>"""


def ficha_html(ficha: dict, seccion: str) -> str:
    datos = []
    for etiqueta, clave in ficha.get("datos", []) or []:
        valor = ficha.get(clave)
        if valor:
            datos.append(f"<dt>{html.escape(etiqueta)}</dt><dd>{html.escape(str(valor))}</dd>")
    bloque_datos = f'<dl class="datos">{"".join(datos)}</dl>' if datos else ""
    return f"""<article class="ficha">
  <header class="ficha-cabecera">
    <p class="migas"><a href="/{seccion}.html">{html.escape(seccion.capitalize())}</a> / {html.escape(ficha['titulo'])}</p>
    <h1>{html.escape(ficha['titulo'])}</h1>
    <p class="sumilla">{html.escape(ficha.get('sumilla', ''))}</p>
  </header>
  {bloque_datos}
  <div class="prosa">
    {md(ficha['_cuerpo'])}
  </div>
</article>"""


def listado(titulo: str, intro: str, fichas: list[dict], base: str, activo: str) -> str:
    tarjetas = "\n".join(tarjeta(f, base) for f in fichas)
    return f"""<section class="cabecera-seccion">
  <h1>{html.escape(titulo)}</h1>
  <p class="entrada">{md(intro)}</p>
</section>
<section class="rejilla">
{tarjetas}
</section>"""


def construir() -> None:
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    SALIDA.mkdir(parents=True)

    # Estáticos
    shutil.copytree(ESTATICO, SALIDA / "estatico")

    # Páginas simples escritas en contenido/paginas
    for archivo in sorted((CONTENIDO / "paginas").glob("*.md")):
        ficha = leer_ficha(archivo)
        destino = SALIDA / (ficha.get("salida") or f"{ficha['_slug']}.html")
        pagina(
            destino,
            f"{ficha['titulo']} — {SITIO['nombre']}",
            f'<section class="cabecera-seccion"><h1>{html.escape(ficha["titulo"])}</h1></section>'
            f'<div class="prosa">{md(ficha["_cuerpo"])}</div>',
            activo=ficha.get("salida", "/"),
            descripcion=ficha.get("descripcion"),
        )

    # Colecciones
    obras = coleccion("obras")
    pedagogia = coleccion("pedagogia")
    investigacion = coleccion("investigacion")
    servicios = coleccion("servicios")

    for ficha in obras:
        pagina(SALIDA / "obra" / f"{ficha['_slug']}.html",
               f"{ficha['titulo']} — {SITIO['nombre']}",
               ficha_html(ficha, "obra"), activo="/obra.html",
               descripcion=ficha.get("sumilla"))

    for ficha in pedagogia:
        pagina(SALIDA / "pedagogia" / f"{ficha['_slug']}.html",
               f"{ficha['titulo']} — {SITIO['nombre']}",
               ficha_html(ficha, "pedagogia"), activo="/pedagogia/",
               descripcion=ficha.get("sumilla"))

    for ficha in investigacion:
        pagina(SALIDA / "investigacion" / f"{ficha['_slug']}.html",
               f"{ficha['titulo']} — {SITIO['nombre']}",
               ficha_html(ficha, "investigacion"), activo="/investigacion/",
               descripcion=ficha.get("sumilla"))

    for ficha in servicios:
        pagina(SALIDA / "estudio" / f"{ficha['_slug']}.html",
               f"{ficha['titulo']} — {SITIO['nombre']}",
               ficha_html(ficha, "estudio"), activo="/estudio/",
               descripcion=ficha.get("sumilla"))

    # Índices de colección
    pagina(SALIDA / "obra.html", f"Obra — {SITIO['nombre']}",
           listado("Obra", (CONTENIDO / "indices/obra.md").read_text(encoding="utf-8").split("---", 2)[2],
                   obras, "obra", "/obra/"), activo="/obra.html")
    pagina(SALIDA / "pedagogia.html", f"Pedagogía — {SITIO['nombre']}",
           listado("Pedagogía", (CONTENIDO / "indices/pedagogia.md").read_text(encoding="utf-8").split("---", 2)[2],
                   pedagogia, "pedagogia", "/pedagogia/"), activo="/pedagogia/")
    pagina(SALIDA / "investigacion.html", f"Investigación — {SITIO['nombre']}",
           listado("Investigación", (CONTENIDO / "indices/investigacion.md").read_text(encoding="utf-8").split("---", 2)[2],
                   investigacion, "investigacion", "/investigacion/"), activo="/investigacion/")
    pagina(SALIDA / "estudio.html", f"Estudio — {SITIO['nombre']}",
           listado("Estudio", (CONTENIDO / "indices/estudio.md").read_text(encoding="utf-8").split("---", 2)[2],
                   servicios, "estudio", "/estudio/"), activo="/estudio/")

    # Portada
    portada = (CONTENIDO / "portada.md").read_text(encoding="utf-8")
    _, _, cuerpo_portada = portada.split("---", 2)
    destacadas = "".join(tarjeta(f, "obra") for f in obras[:3])
    pagina(SALIDA / "index.html", SITIO["nombre"],
           f'<div class="prosa">{md(cuerpo_portada)}</div>'
           f'<section class="destacadas"><h2>Obra reciente</h2><div class="rejilla">{destacadas}</div></section>',
           activo="/", clase="portada")

    # 404
    pagina(SALIDA / "404.html", f"No encontrado — {SITIO['nombre']}",
           '<section class="cabecera-seccion"><h1>404</h1>'
           '<p class="entrada">Esta página no existe o cambió de lugar. '
           '<a href="/">Volver al inicio</a>.</p></section>')

    # Archivos de publicación
    (SALIDA / ".nojekyll").write_text("", encoding="utf-8")
    (SALIDA / "CNAME").write_text(SITIO["dominio"] + "\n", encoding="utf-8")
    (SALIDA / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: https://{SITIO['dominio']}/sitemap.xml\n", encoding="utf-8")
    (SALIDA / "sitemap.xml").write_text(sitemap(), encoding="utf-8")

    print(f"Sitio generado en {SALIDA}")
    print(f"  obras: {len(obras)} | pedagogía: {len(pedagogia)} | "
          f"investigación: {len(investigacion)} | estudio: {len(servicios)}")


def sitemap() -> str:
    urls = []
    for ruta in sorted(SALIDA.rglob("*.html")):
        rel = ruta.relative_to(SALIDA).as_posix()
        if rel == "404.html":
            continue
        loc = "/" if rel == "index.html" else f"/{rel}"
        urls.append(f"<url><loc>https://{SITIO['dominio']}{loc}</loc></url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls) + "\n</urlset>\n")


if __name__ == "__main__":
    construir()
