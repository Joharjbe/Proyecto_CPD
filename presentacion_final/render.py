"""Exporta la presentación (fuente/deck.json + fuente/slides/*.html) a presentacion_final.pdf.

Imita las reglas del formato del deck: lienzo de 1920x1080, margin 0 y box-sizing border-box,
un <div> sin display es una columna flex, tamaños por defecto de h1-h3 y p, x-shape ellipse y
x-connector recto con punta llena al final. El <aside> es la nota del orador: no se dibuja y se
guarda en build/notas.json para el PPTX. No hay animaciones.
"""
import hashlib
import html
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

AQUI = pathlib.Path(__file__).resolve().parent
PROJ = AQUI / "fuente"
REPO = AQUI.parent
BUILD = AQUI / "build"
FONTS = BUILD / "fonts"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

deck = json.loads((PROJ / "deck.json").read_text(encoding="utf-8"))
order = deck["order"]
IMAGENES = json.loads((PROJ / "imagenes.json").read_text(encoding="utf-8"))


def chrome():
    if os.environ.get("CHROME"):
        return pathlib.Path(os.environ["CHROME"])
    for base in (pathlib.Path.home() / "Library/Caches/ms-playwright", pathlib.Path.home() / ".cache/ms-playwright"):
        for c in sorted(base.glob("chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"), reverse=True):
            return c
    sys.exit("No encontré chrome-headless-shell: instálalo con 'python -m playwright install chromium-headless-shell' "
             "o define CHROME=/ruta/a/chrome")


def fuentes_locales():
    """Baja las woff2 de Google Fonts a build/fonts y devuelve el CSS con rutas locales."""
    FONTS.mkdir(parents=True, exist_ok=True)
    css_total = []
    for clave, cara in deck["faces"].items():
        css = urllib.request.urlopen(urllib.request.Request(cara["href"], headers={"User-Agent": UA}), timeout=30).read().decode()
        for url in sorted(set(re.findall(r"url\((https://[^)]+)\)", css))):
            # el nombre sale de la URL, así el caché no confunde dos compilaciones de la misma tipografía
            destino = FONTS / f"{clave}-{hashlib.sha1(url.encode()).hexdigest()[:12]}.woff2"
            if not destino.exists():
                destino.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read())
            css = css.replace(url, destino.as_uri())
        css_total.append(css.replace("font-display: swap", "font-display: block"))
    return "\n".join(css_total)


def atributos(tag):
    return {k: html.unescape(v) for k, v in re.findall(r'([\w-]+)="([^"]*)"', tag)}


def estilo(s):
    out = {}
    for parte in s.split(";"):
        if ":" in parte:
            k, v = parte.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def conector(m):
    a = atributos(m.group(0))
    st = estilo(a.get("style", ""))
    color = st.get("color", "#000000")
    w = float(re.sub(r"[^0-9.]", "", st.get("border-width", "2")) or 2)
    x1, y1, x2, y2 = (float(a[k]) for k in ("x1", "y1", "x2", "y2"))
    if a.get("route", "straight") != "straight":
        sys.exit(f"ruta de conector no soportada: {a.get('route')}")
    head = a.get("head", "end")
    dash = ' stroke-dasharray="%g %g"' % (3 * w, 2 * w) if "dashed" in st.get("border-style", "") else ""
    d = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    px, py = -uy, ux
    largo, medio = 4 * w, 2 * w  # punta de tamaño constante: unos 4 trazos

    def punta(tx, ty, sx, sy):
        bx, by = tx - sx * largo, ty - sy * largo
        pts = f"{tx:.1f},{ty:.1f} {bx + px * medio:.1f},{by + py * medio:.1f} {bx - px * medio:.1f},{by - py * medio:.1f}"
        return (f'<polygon points="{pts}" fill="{color}" stroke="{color}" stroke-width="{w * 0.5:g}" stroke-linejoin="round"/>',
                (bx + sx * w * 0.4, by + sy * w * 0.4))

    partes, lx1, ly1, lx2, ly2 = [], x1, y1, x2, y2
    if head in ("end", "both") and a.get("head-end", "filled") != "none":
        poly, (lx2, ly2) = punta(x2, y2, ux, uy)
        partes.append(poly)
    if head == "both" and a.get("head-start", "filled") != "none":
        poly, (lx1, ly1) = punta(x1, y1, -ux, -uy)
        partes.append(poly)
    linea = (f'<line x1="{lx1:.1f}" y1="{ly1:.1f}" x2="{lx2:.1f}" y2="{ly2:.1f}" stroke="{color}" '
             f'stroke-width="{w:g}" stroke-linecap="round"{dash}/>')
    return ('<svg width="1920" height="1080" viewBox="0 0 1920 1080" style="position:absolute; left:0; top:0; overflow:visible">'
            + linea + "".join(partes) + "</svg>")


def forma(m):
    a = atributos(m.group(0))
    kind, st = a.get("kind", "rect"), html.escape(a.get("style", ""), quote=True)
    if kind == "ellipse":
        return f'<div style="{st}; border-radius:50%"></div>'
    if kind == "rect":
        return f'<div style="{st}"></div>'
    sys.exit(f"x-shape no soportada: {kind}")


def imagen(m):
    ruta = IMAGENES.get(m.group(1))
    if not ruta:
        sys.exit(f"imagen sin mapear en fuente/imagenes.json: {m.group(1)}")
    return f'src="{(REPO / ruta).as_uri()}"'


notas, paginas = {}, []
for sid in order:
    src = (PROJ / "slides" / f"{sid}.html").read_text(encoding="utf-8")
    m = re.search(r"<aside>(.*?)</aside>", src, re.S)
    notas[sid] = html.unescape(m.group(1)).strip() if m else ""
    src = re.sub(r"<aside>.*?</aside>", "", src, flags=re.S)
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    src = re.sub(r"<x-connector\b[^>]*>\s*</x-connector>", conector, src)
    src = re.sub(r"<x-shape\b[^>]*>\s*</x-shape>", forma, src)
    src = re.sub(r'src="/_blob/([0-9a-f]{32})"', imagen, src)
    if re.search(r"<x-|/_blob/", src):
        sys.exit(f"{sid}: quedó un elemento sin convertir")
    paginas.append(f'<div class="page">{src}</div>')

CSS = """
@page { size: 1920px 1080px; margin: 0; }
html, body { margin: 0; padding: 0; background: #ffffff; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 1920px; height: 1080px; overflow: hidden; position: relative; break-after: page; page-break-after: always; }
.page:last-child { break-after: auto; page-break-after: auto; }
section { position: relative; width: 1920px; height: 1080px; overflow: hidden; display: flex; flex-direction: column; font-size: 32px; }
div { display: flex; flex-direction: column; }
h1 { font-size: 96px; font-weight: 600; line-height: 1.1; }
h2 { font-size: 64px; font-weight: 600; line-height: 1.15; }
h3 { font-size: 44px; font-weight: 600; line-height: 1.2; }
p { line-height: 1.4; }
h1, h2, h3, p, li, td, th { overflow-wrap: break-word; }
ul, ol { padding-left: 1.25em; }
table { border-collapse: separate; border-spacing: 0; }
th, td { padding: 0.35em 0.6em; text-align: left; vertical-align: top; }
tr + tr > td, tr + tr > th { border-top: 1px solid rgba(16, 28, 46, 0.12); }
th { font-weight: 600; }
img { display: block; }
aside { display: none; }
"""

BUILD.mkdir(exist_ok=True)
doc = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{html.escape(deck["title"])}</title>'
       f"<style>{fuentes_locales()}\n{CSS}</style></head><body>{''.join(paginas)}</body></html>")
(BUILD / "deck_render.html").write_text(doc, encoding="utf-8")
(BUILD / "notas.json").write_text(json.dumps({"order": order, "notas": notas}, ensure_ascii=False, indent=1), encoding="utf-8")

pdf = AQUI / "presentacion_final.pdf"
subprocess.run([str(chrome()), "--headless", "--disable-gpu", "--no-pdf-header-footer", "--hide-scrollbars",
                "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000",
                f"--print-to-pdf={pdf}", (BUILD / "deck_render.html").as_uri()], check=True, capture_output=True)
print("PDF:", pdf, pdf.stat().st_size, "bytes,", len(order), "diapositivas")
