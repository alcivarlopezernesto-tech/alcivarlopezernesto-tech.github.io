#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generador del sitio de Cadenza Inc. — bilingüe español / inglés.

Lee los archivos Markdown de contenido/ y produce el sitio estático en docs/,
que es la carpeta que GitHub Pages publica (rama main, carpeta /docs).

Cada página vive en un solo archivo: el cuerpo español primero, el marcador
<!--:en--> y luego el cuerpo inglés. Los campos de portada que cambian de
idioma llevan su pareja con el sufijo _en (titulo_en, sumilla_en, …). Las
cadenas con dos versiones en una sola línea usan la forma "Español|English",
por ejemplo en las etiquetas de la tabla de datos o en los enlaces.

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
UI = MARCA["interfaz"]

MD = markdown.Markdown(extensions=["extra", "tables", "attr_list", "md_in_html"])

SEPARADOR_EN = "<!--:en-->"

# Nombre de la sección en las migas y en el título de la pestaña.
SECCIONES = {
    "obra": ("Obra", "Work"),
    "pedagogia": ("Pedagogía", "Teaching"),
    "investigacion": ("Investigación", "Research"),
    "estudio": ("Estudio", "Studio"),
}


# --------------------------------------------------------------------------
# Utilidades bilingües
# --------------------------------------------------------------------------

def bi(es, en=None) -> str:
    """Devuelve un texto con sus dos versiones; el idioma activo decide cuál se ve."""
    es_txt = html.escape(str(es if es is not None else ""))
    en_txt = html.escape(str(en if en else (es if es is not None else "")))
    return (f'<span data-lang="es">{es_txt}</span>'
            f'<span data-lang="en">{en_txt}</span>')


def bi_md(es, en=None) -> str:
    """Igual que bi(), para bloques que hay que interpretar como Markdown."""
    es_txt = md(str(es if es is not None else ""))
    en_txt = md(str(en if en else (es if es is not None else "")))
    return (f'<div data-lang="es">{es_txt}</div>'
            f'<div data-lang="en">{en_txt}</div>')


def par(ficha: dict, clave: str, defecto: str = "") -> tuple[str, str]:
    """Valor español y su pareja inglesa (clave_en), con vuelta al español si falta."""
    es = ficha.get(clave, defecto)
    en = ficha.get(f"{clave}_en")
    if en in (None, ""):
        en = es
    return es, en


def partir_etiqueta(texto) -> tuple[str, str]:
    """«TIPO|TYPE» → ("TIPO", "TYPE"); sin barra, la misma etiqueta en los dos idiomas."""
    partes = str(texto).split("|", 1)
    if len(partes) == 2:
        return partes[0].strip(), partes[1].strip()
    return partes[0].strip(), partes[0].strip()


# --------------------------------------------------------------------------
# Lectura de contenido
# --------------------------------------------------------------------------

def leer_ficha(ruta: Path) -> dict:
    """Separa front matter YAML del cuerpo Markdown y parte el cuerpo por idioma."""
    texto = ruta.read_text(encoding="utf-8")
    if not texto.startswith("---"):
        raise ValueError(f"Sin front matter: {ruta}")
    _, fm, resto = texto.split("---", 2)
    datos = yaml.safe_load(fm) or {}
    if SEPARADOR_EN in resto:
        cuerpo_es, cuerpo_en = resto.split(SEPARADOR_EN, 1)
    else:
        cuerpo_es, cuerpo_en = resto, ""
    datos["_cuerpo"] = cuerpo_es.strip()
    datos["_cuerpo_en"] = cuerpo_en.strip()
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


# --------------------------------------------------------------------------
# Piezas de plantilla
# --------------------------------------------------------------------------

def nav_html(activo: str) -> str:
    partes = []
    for item in NAV:
        clase = ' class="activo"' if item["url"].strip("/") == activo.strip("/") else ""
        etiqueta = bi(item["titulo"], item.get("titulo_en"))
        partes.append(f'<a href="{item["url"]}"{clase}>{etiqueta}</a>')
    return "\n      ".join(partes)


def pagina(destino: Path, titulo: str, cuerpo: str, activo: str = "",
           descripcion: str | None = None, clase: str = "",
           titulo_en: str | None = None, descripcion_en: str | None = None) -> None:
    plantilla = Template((PLANTILLAS / "base.html").read_text(encoding="utf-8"))
    destino.parent.mkdir(parents=True, exist_ok=True)
    desc_es = html.escape(descripcion or SITIO["descripcion"])
    desc_en = html.escape(descripcion_en or descripcion or SITIO["descripcion"])
    destino.write_text(
        plantilla.substitute(
            titulo=html.escape(titulo),
            titulo_en=html.escape(titulo_en or titulo),
            titulo_sitio=SITIO["nombre"],
            descripcion=desc_es,
            descripcion_en=desc_en,
            cuerpo=cuerpo,
            nav=nav_html(activo),
            lema=SITIO["lema"],
            correo=SITIO["correo"],
            anio=SITIO["anio"],
            clase=clase,
            salto=bi(*UI["salto"]),
            derechos=bi(*UI["derechos"]),
            idioma_etiqueta=UI["idioma_etiqueta"],
        ),
        encoding="utf-8",
    )


def tarjeta(ficha: dict, base: str) -> str:
    meta_es, meta_en = par(ficha, "meta")
    if not meta_es:
        meta_es, meta_en = par(ficha, "resumen")
    sumilla = par(ficha, "sumilla")
    return f"""<a class="tarjeta" href="/{base}/{ficha['_slug']}.html">
  <span class="tarjeta-meta">{bi(meta_es, meta_en)}</span>
  <h3>{bi(ficha['titulo'], ficha.get('titulo_en'))}</h3>
  <p>{bi(sumilla[0], sumilla[1])}</p>
</a>"""


ICONOS = {
    "play": '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.6v8.8l7-4.4z"/></svg>',
}


def bloque_enlaces(ficha: dict) -> str:
    """Botones de enlace externo declarados en el front matter:

    enlaces:
      - ["Etiqueta|Label", "https://…", "play"]   # icono opcional
    """
    botones = []
    for item in ficha.get("enlaces", []) or []:
        if len(item) < 2:
            continue
        etiqueta_es, etiqueta_en = partir_etiqueta(item[0])
        url = str(item[1])
        icono = ICONOS.get(str(item[2]), "") if len(item) > 2 else ""
        botones.append(
            f'<a class="boton" href="{html.escape(url)}" target="_blank" rel="noopener">'
            f'{icono}{bi(etiqueta_es, etiqueta_en)}</a>'
        )
    if not botones:
        return ""
    return f'<div class="botones">{"".join(botones)}</div>'


def bloque_galeria(ficha: dict) -> str:
    """Miniaturas de video declaradas en el front matter:

    galeria:
      - ["ID_de_YouTube", "Título", "Meta opcional"]
    """
    celdas = []
    for item in ficha.get("galeria", []) or []:
        if len(item) < 2:
            continue
        vid, titulo = str(item[0]), str(item[1])
        meta = str(item[2]) if len(item) > 2 else ""
        detalle = f'<span class="miniatura-meta">{html.escape(meta)}</span>' if meta else ""
        celdas.append(
            f'<a class="miniatura" href="https://www.youtube.com/watch?v={html.escape(vid)}"'
            f' target="_blank" rel="noopener">'
            f'<span class="miniatura-marco">'
            f'<img src="/estatico/img/miniaturas/{html.escape(vid)}.jpg"'
            f' alt="Video: {html.escape(titulo)}" width="640" height="360" loading="lazy">'
            f'<span class="miniatura-play" aria-hidden="true"></span>'
            f'</span>'
            f'<span class="miniatura-titulo">{html.escape(titulo)}</span>'
            f'{detalle}</a>'
        )
    if not celdas:
        return ""
    return f'<div class="galeria">{"".join(celdas)}</div>'


def bloque_datos(ficha: dict) -> str:
    datos = []
    for fila in ficha.get("datos", []) or []:
        if len(fila) < 2:
            continue
        etiqueta_es, etiqueta_en = partir_etiqueta(fila[0])
        valor_es, valor_en = par(ficha, str(fila[1]))
        if not valor_es:
            continue
        datos.append(
            f"<dt>{bi(etiqueta_es, etiqueta_en)}</dt>"
            f"<dd>{bi(valor_es, valor_en)}</dd>"
        )
    if not datos:
        return ""
    return f'<dl class="datos">{"".join(datos)}</dl>'


def bloque_descargas(ficha: dict) -> str:
    """Tabla de documentos descargables declarada en el front matter:

    descargas:
      - grupo: "Planificación|Planning"
        nota: "Versión del autor|Author's version"
        filas:
          - ["Título|Title", "archivo.pdf", 5]
    """
    grupos = ficha.get("descargas") or []
    if not grupos:
        return ""
    salida = []
    for g in grupos:
        titulo_es, titulo_en = partir_etiqueta(g.get("grupo", ""))
        filas = []
        for fila in g.get("filas", []) or []:
            if len(fila) < 2:
                continue
            tit_es, tit_en = partir_etiqueta(fila[0])
            archivo = str(fila[1])
            paginas = str(fila[2]) if len(fila) > 2 else ""
            ruta = ESTATICO / "pdf" / archivo
            if not ruta.exists():
                continue  # aún no publicado
            peso = f"{ruta.stat().st_size / 1024:.0f} KB"
            filas.append(
                f'<tr><td class="desc-titulo">'
                f'<a href="/estatico/pdf/{html.escape(archivo)}" download>{bi(tit_es, tit_en)}</a>'
                f'</td><td class="desc-num">{html.escape(paginas)}</td>'
                f'<td class="desc-num">{peso}</td></tr>'
            )
        if not filas:
            continue
        nota = ""
        if g.get("nota"):
            n_es, n_en = partir_etiqueta(g["nota"])
            nota = f'<p class="desc-nota">{bi(n_es, n_en)}</p>'
        salida.append(
            f'<section class="descargas">\n'
            f'  <h2>{bi(titulo_es, titulo_en)}</h2>\n'
            f'  {nota}\n'
            f'  <table>\n'
            f'    <thead><tr><th>{bi("Documento", "Document")}</th>'
            f'<th class="desc-num">{bi("Páginas", "Pages")}</th>'
            f'<th class="desc-num">{bi("Peso", "Size")}</th></tr></thead>\n'
            f'    <tbody>{"".join(filas)}</tbody>\n'
            f'  </table>\n'
            f'</section>'
        )
    return "\n".join(salida)


def ficha_html(ficha: dict, seccion: str) -> str:
    seccion_es, seccion_en = SECCIONES.get(seccion, (seccion.capitalize(), seccion.capitalize()))
    galeria = bloque_galeria(ficha)
    descargas = bloque_descargas(ficha)
    clase_ficha = ' class="ficha ficha-ancha"' if galeria else ' class="ficha"'
    cuerpo = md(ficha["_cuerpo"])
    cuerpo_en = md(ficha["_cuerpo_en"]) if ficha.get("_cuerpo_en") else cuerpo
    return f"""<article{clase_ficha}>
  <header class="ficha-cabecera">
    <p class="migas"><a href="/{seccion}.html">{bi(seccion_es, seccion_en)}</a> / {bi(ficha['titulo'], ficha.get('titulo_en'))}</p>
    <h1>{bi(ficha['titulo'], ficha.get('titulo_en'))}</h1>
    <p class="sumilla">{bi(par(ficha, 'sumilla')[0], par(ficha, 'sumilla')[1])}</p>
  </header>
  {bloque_enlaces(ficha)}
  {galeria}
  {bloque_datos(ficha)}
  <div class="prosa" data-lang="es">
    {cuerpo}
  </div>
  <div class="prosa" data-lang="en">
    {cuerpo_en}
  </div>
  {descargas}
</article>"""


def listado(titulo: str, titulo_en: str, intro_es: str, intro_en: str,
            fichas: list[dict], base: str) -> str:
    tarjetas = "\n".join(tarjeta(f, base) for f in fichas)
    return f"""<section class="cabecera-seccion">
  <h1>{bi(titulo, titulo_en)}</h1>
  {bi_md(intro_es, intro_en)}
</section>
<section class="rejilla">
{tarjetas}
</section>"""


# --------------------------------------------------------------------------
# Construcción
# --------------------------------------------------------------------------

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
        cuerpo_en = md(ficha["_cuerpo_en"]) if ficha.get("_cuerpo_en") else md(ficha["_cuerpo"])
        pagina(
            destino,
            f"{ficha['titulo']} — {SITIO['nombre']}",
            f'<section class="cabecera-seccion"><h1>{bi(ficha["titulo"], ficha.get("titulo_en"))}</h1></section>'
            f'<div class="prosa" data-lang="es">{md(ficha["_cuerpo"])}</div>'
            f'<div class="prosa" data-lang="en">{cuerpo_en}</div>',
            activo=ficha.get("salida", "/"),
            descripcion=ficha.get("descripcion"),
            titulo_en=f"{ficha.get('titulo_en') or ficha['titulo']} — {SITIO['nombre']}",
            descripcion_en=ficha.get("descripcion_en"),
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
               descripcion=par(ficha, "sumilla")[0],
               titulo_en=f"{ficha.get('titulo_en') or ficha['titulo']} — {SITIO['nombre']}",
               descripcion_en=par(ficha, "sumilla")[1])

    for ficha in pedagogia:
        pagina(SALIDA / "pedagogia" / f"{ficha['_slug']}.html",
               f"{ficha['titulo']} — {SITIO['nombre']}",
               ficha_html(ficha, "pedagogia"), activo="/pedagogia/",
               descripcion=par(ficha, "sumilla")[0],
               titulo_en=f"{ficha.get('titulo_en') or ficha['titulo']} — {SITIO['nombre']}",
               descripcion_en=par(ficha, "sumilla")[1])

    for ficha in investigacion:
        pagina(SALIDA / "investigacion" / f"{ficha['_slug']}.html",
               f"{ficha['titulo']} — {SITIO['nombre']}",
               ficha_html(ficha, "investigacion"), activo="/investigacion/",
               descripcion=par(ficha, "sumilla")[0],
               titulo_en=f"{ficha.get('titulo_en') or ficha['titulo']} — {SITIO['nombre']}",
               descripcion_en=par(ficha, "sumilla")[1])

    for ficha in servicios:
        pagina(SALIDA / "estudio" / f"{ficha['_slug']}.html",
               f"{ficha['titulo']} — {SITIO['nombre']}",
               ficha_html(ficha, "estudio"), activo="/estudio/",
               descripcion=par(ficha, "sumilla")[0],
               titulo_en=f"{ficha.get('titulo_en') or ficha['titulo']} — {SITIO['nombre']}",
               descripcion_en=par(ficha, "sumilla")[1])

    # Índices de colección
    indices = {
        "obra": (obras, "obra"),
        "pedagogia": (pedagogia, "pedagogia"),
        "investigacion": (investigacion, "investigacion"),
        "estudio": (servicios, "estudio"),
    }
    for nombre, (fichas, base) in indices.items():
        indice = leer_ficha(CONTENIDO / f"indices/{nombre}.md")
        titulo_es, titulo_en = SECCIONES[nombre]
        pagina(SALIDA / f"{nombre}.html",
               f"{titulo_es} — {SITIO['nombre']}",
               listado(titulo_es, titulo_en, indice["_cuerpo"], indice.get("_cuerpo_en") or indice["_cuerpo"],
                       fichas, base),
               activo=f"/{nombre}.html",
               descripcion=indice.get("descripcion"),
               titulo_en=f"{titulo_en} — {SITIO['nombre']}",
               descripcion_en=indice.get("descripcion_en"))

    # Portada
    portada = leer_ficha(CONTENIDO / "portada.md")
    destacadas = "".join(tarjeta(f, "obra") for f in obras[:3])
    cuerpo_en = md(portada["_cuerpo_en"]) if portada.get("_cuerpo_en") else md(portada["_cuerpo"])
    pagina(SALIDA / "index.html", SITIO["nombre"],
           f'<div class="prosa" data-lang="es">{md(portada["_cuerpo"])}</div>'
           f'<div class="prosa" data-lang="en">{cuerpo_en}</div>'
           f'<section class="destacadas"><h2>{bi(*UI["obra_reciente"])}</h2>'
           f'<div class="rejilla">{destacadas}</div></section>',
           activo="/", clase="portada",
           titulo_en=SITIO.get("nombre_en") or SITIO["nombre"],
           descripcion_en=SITIO.get("descripcion_en"))

    # 404
    pagina(SALIDA / "404.html",
           f"{UI['no_encontrado'][0]} — {SITIO['nombre']}",
           '<section class="cabecera-seccion"><h1>404</h1>'
           f'<p class="entrada">{bi(*UI["no_encontrado_texto"])} '
           f'<a href="/">{bi(*UI["volver_inicio"])}</a>.</p></section>',
           titulo_en=f"{UI['no_encontrado'][1]} — {SITIO['nombre']}",
           descripcion_en=UI["no_encontrado_texto"][1])

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
