# Cadenza Inc. — sitio

Sitio estático de la marca **Cadenza Inc.** Composición, arreglo, pedagogía musical e investigación aplicada. Autor: Ernesto Alcívar López.

- Dominio: `cadenzainc.com`
- Publicación: GitHub Pages, rama `main`, carpeta `/docs`
- Generador: `build.py` (Python + markdown + PyYAML)

## Construir

```bash
python3 build.py
```

Genera `docs/` con las 30 páginas, el CSS, las imágenes, `sitemap.xml`, `robots.txt` y `CNAME`.

## Verificar antes de publicar

```bash
python3 verificar_exclusion.py   # bloquea material fuera del objeto del sitio
python3 verificar_sitio.py       # comprueba enlaces internos
```

Si `verificar_exclusion.py` falla, **no se publica**.

## Publicar

```bash
git add docs
git commit -m "Publicación"
git push
```

GitHub Pages sirve `docs/` tal cual, sin compilar: el sitio no depende de Jekyll.

## Estructura

```
contenido/     fichas en Markdown con front matter
plantillas/    base.html
estatico/      css, imágenes, pdf
docs/          salida publicada (no editar a mano)
build.py       generador
verificar_exclusion.py
verificar_sitio.py
```

## Agregar una obra

Crear `contenido/obras/mi-obra.md`:

```yaml
---
titulo: "Título"
sumilla: "Una línea."
meta: "Orquesta · 8 min"
anio: 2026
datos:
  - ["Instrumentación", "orquesta"]
  - ["Duración", "8 min"]
---
Texto de la ficha.
```

Luego `python3 build.py`.

## Regla editorial

Este repositorio se limita al objeto del sitio: composición, pedagogía musical e investigación aplicada. Las carpetas personales ajenas a ese objeto están excluidas por nombre en `.gitignore` y bloqueadas por `verificar_exclusion.py`, que revisa nombres, texto e historial de git.

El logo y la paleta (negro `#000000`, oro `#F7B30A`, blanco) provienen del logotipo oficial.
