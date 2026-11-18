# Presentación final: fuente editable

La presentación se hizo como un deck de claude.ai (tipo Slides). El PDF y el PPTX de esta carpeta se generan desde `fuente/`. En el PPTX cada diapositiva es una imagen y las notas del orador van como texto.

| Archivo | Qué es |
|---|---|
| `fuente/deck.json` | Orden de las 19 diapositivas, secciones y tipografías |
| `fuente/slides/<id>.html` | Una diapositiva por archivo (lienzo de 1920 × 1080 px). La nota del orador va en el `<aside>` del final |
| `fuente/imagenes.json` | A qué archivo corresponde cada `/_blob/<id>`: 8 son figuras de `codigo/resultados/figuras/png/` y 6 están en `fuente/img/` |
| `render.py` | Genera `presentacion_final.pdf` con Chrome headless y deja las notas en `build/notas.json` |
| `armar_pptx.py` | Genera `presentacion_final.pptx`: una imagen por diapositiva (144 dpi) con su nota |

## Corregir una diapositiva

1. Editar el texto, las cifras o la nota en `fuente/slides/<id>.html`. El orden está en `deck.json`; por ejemplo, la 12 es `popt.html`. No tocar los `src="/_blob/..."`.
2. Si cambia una figura de resultados, se regenera con `python analisis.py` desde `codigo/`.
3. Regenerar el PDF y el PPTX y revisar el PDF página por página.

## Regenerar el PDF y el PPTX (macOS o Linux, Python 3.11)

```bash
pip install python-pptx playwright
python -m playwright install chromium-headless-shell   # o definir CHROME=/ruta/a/chrome
brew install poppler                                    # pdftoppm (en Linux: apt install poppler-utils)
cd presentacion_final
python render.py        # presentacion_final.pdf (necesita internet para las tipografías)
python armar_pptx.py    # presentacion_final.pptx
```

`render.py` imita el formato del deck (sin animaciones) y se detiene si queda un elemento sin convertir. Las tipografías se bajan de Google Fonts en cada corrida; si Google sirve otra compilación de una de ellas, el PDF puede cambiar levemente, sin que se note a simple vista. El deck en vivo está en claude.ai y solo Johar puede editarlo: si se corrige aquí, hay que avisarle para que suba el mismo HTML.
