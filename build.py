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
import re
import hashlib
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

# Dominio propio del sitio. Mientras no esté registrado o no apunte a GitHub
# Pages, se deja vacío y el sitio se publica en la dirección de GitHub Pages;
# el archivo CNAME solo se genera cuando hay dominio, y el sitemap apunta
# siempre a la dirección donde el sitio responde de verdad.
DIRECCION_PAGES = "alcivarlopezernesto-tech.github.io"
DOMINIO = str(SITIO.get("dominio") or "").strip()
DOMINIO_URL = DOMINIO or DIRECCION_PAGES
URL_BASE = f"https://{DOMINIO_URL}"

MD = markdown.Markdown(extensions=["extra", "tables", "attr_list", "md_in_html"])

# Huella de los estáticos: va en la URL del CSS y del JS para que el navegador no
# siga sirviendo la versión vieja después de un despliegue (GitHub Pages cachea
# los archivos 10 minutos y eso hacía que los cambios de estilo "no se vieran").
VERSION_CSS = hashlib.md5((ESTATICO / "css" / "estilo.css").read_bytes()).hexdigest()[:8]
VERSION_JS = hashlib.md5((ESTATICO / "js" / "idioma.js").read_bytes()).hexdigest()[:8]

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
            url_base=URL_BASE,
            ruta="/" if destino.name == "index.html" else "/" + destino.name,
            salto=bi(*UI["salto"]),
            derechos=bi(*UI["derechos"]),
            idioma_etiqueta=UI["idioma_etiqueta"],
            redes=redes_html(),
            version_css=VERSION_CSS,
            version_js=VERSION_JS,
        ),
        encoding="utf-8",
    )


def tarjeta(ficha: dict, base: str) -> str:
    meta_es, meta_en = par(ficha, "meta")
    if not meta_es:
        meta_es, meta_en = par(ficha, "resumen")
    sumilla = par(ficha, "sumilla")
    url_yt = url_youtube(ficha)
    titulo = bi(ficha["titulo"], ficha.get("titulo_en"))
    if not url_yt:
        return f"""<a class="tarjeta" href="/{base}/{ficha['_slug']}.html">
  <span class="tarjeta-meta">{bi(meta_es, meta_en)}</span>
  <h3>{titulo}</h3>
  <p>{bi(sumilla[0], sumilla[1])}</p>
</a>"""
    # Ficha con video publicado: la tarjeta deja de ser un enlace único para poder
    # llevar el logo de YouTube junto al título. El título se estira sobre toda la
    # tarjeta (patrón de enlace estirado) y el logo queda por encima, así el resto
    # de la tarjeta sigue abriendo la ficha y el logo va directo a la lista.
    return f"""<div class="tarjeta tarjeta-yt">
  <span class="tarjeta-meta">{bi(meta_es, meta_en)}</span>
  <h3><a class="estira" href="/{base}/{ficha['_slug']}.html">{titulo}</a><a class="ico-yt-enlace" href="{html.escape(url_yt)}" target="_blank" rel="noopener" aria-label="YouTube">{ICONOS['youtube']}</a></h3>
  <p>{bi(sumilla[0], sumilla[1])}</p>
</div>"""


ICONOS = {
    "play": '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.6v8.8l7-4.4z"/></svg>',
    # Logotipo de YouTube en su forma y color oficiales (rojo #FF0000, triángulo
    # blanco): las guías de marca de la plataforma prohíben recolorearlo.
    "youtube": (
        '<svg class="ico-yt" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<path class="cuerpo" d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 '
        '0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 '
        '2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 '
        '24 12s0-3.93-.502-5.814z"/>'
        '<path d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z" fill="#fff"/></svg>'
    ),
}


# Iconos de las redes donde Cadenza Inc. tiene o tendrá presencia.
# Trazo oficial (simple-icons) y color de marca; TikTok va en blanco porque el
# negro del logo desaparece sobre el fondo negro del sitio.
REDES_ICONOS = {
    "youtube": ("M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z", "#FF0000"),
    "facebook": ("M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z", "#0866FF"),
    "instagram": ("M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077", "#E4405F"),
    "telegram": ("M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z", "#26A5E4"),
    "tiktok": ("M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z", "#FFFFFF"),
    "linkedin": ("M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z", "#0A66C2"),
}

def redes_html() -> str:
    """Fila de iconos del pie. Solo se dibujan las redes con url en marca.yml:
    nunca se publica un enlace a un perfil que todavía no existe."""
    enlaces = []
    for red in MARCA.get("redes", []) or []:
        icono = REDES_ICONOS.get(str(red.get("icono") or ""))
        if not icono:
            continue
        trazo, color = icono
        nombre = str(red.get("nombre") or red.get("icono"))
        url = str(red.get("url") or "").strip()
        svg = (f'<svg class="ico-red" viewBox="0 0 24 24" aria-hidden="true" '
               f'focusable="false"><path fill="{color}" d="{trazo}"/></svg>')
        if url:
            enlaces.append(
                f'<a href="{html.escape(url)}" target="_blank" rel="noopener me" '
                f'aria-label="{html.escape(nombre)}" title="{html.escape(nombre)}">{svg}</a>')
        else:
            # Sin perfil todavía: el icono se ve, pero no es un enlace muerto.
            enlaces.append(
                f'<span class="redes-pendiente" role="img" aria-label="{html.escape(nombre)}" '
                f'title="{html.escape(nombre)} — perfil en preparación">{svg}</span>')
    if not enlaces:
        return ""
    return ('<nav class="redes" aria-label="Redes sociales">' + "".join(enlaces) + "</nav>")


def url_youtube(ficha: dict) -> str:
    """Enlace de YouTube de la ficha: prioriza la lista de reproducción, que agrupa
    la obra, sobre un video suelto. Devuelve \"\" si la ficha no tiene video."""
    enlaces = [str(item[1]) for item in (ficha.get("enlaces") or []) if len(item) > 1]
    for url in enlaces:
        if "list=" in url and ("youtube.com" in url or "youtu.be" in url):
            return url
    for url in enlaces:
        if "youtube.com" in url or "youtu.be" in url:
            return url
    for item in ficha.get("galeria", []) or []:
        if item and item[0]:
            return f"https://www.youtube.com/watch?v={item[0]}"
    return ""


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
            clase=ficha.get("clase", ""),
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

    # El 404 no se indexa ni se canoniza
    _404 = SALIDA / "404.html"
    if _404.exists():
        _h = _404.read_text(encoding="utf-8")
        _h = re.sub(r'<link rel="canonical"[^>]*>\n?', "", _h)
        _h = _h.replace('<meta name="viewport"', '<meta name="robots" content="noindex">\n<meta name="viewport"', 1)
        _404.write_text(_h, encoding="utf-8")

    # Archivos de publicación
    (SALIDA / ".nojekyll").write_text("", encoding="utf-8")
    if DOMINIO:
        (SALIDA / "CNAME").write_text(DOMINIO + "\n", encoding="utf-8")
    (SALIDA / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: https://{DOMINIO_URL}/sitemap.xml\n", encoding="utf-8")
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
        urls.append(f"<url><loc>https://{DOMINIO_URL}{loc}</loc></url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls) + "\n</urlset>\n")


if __name__ == "__main__":
    construir()
