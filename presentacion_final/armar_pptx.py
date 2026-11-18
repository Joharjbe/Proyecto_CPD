"""Arma presentacion_final.pptx a partir de presentacion_final.pdf: una imagen por diapositiva
(16:9, a pantalla completa, 144 dpi) y la nota del orador de cada <aside> como nota de PowerPoint.
Correr después de render.py, que deja las notas en build/notas.json."""
import json
import pathlib
import subprocess

from pptx import Presentation
from pptx.util import Emu

AQUI = pathlib.Path(__file__).resolve().parent
BUILD = AQUI / "build"
HD = BUILD / "png_hd"
pdf = AQUI / "presentacion_final.pdf"
datos = json.loads((BUILD / "notas.json").read_text(encoding="utf-8"))
order, notas = datos["order"], datos["notas"]

HD.mkdir(parents=True, exist_ok=True)
for f in HD.glob("*.png"):
    f.unlink()
subprocess.run(["pdftoppm", "-r", "144", "-png", str(pdf), str(HD / "s")], check=True, capture_output=True)
imgs = sorted(HD.glob("s-*.png"))
assert len(imgs) == len(order), (len(imgs), len(order))

prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)  # 13,333 x 7,5 in (16:9)
for img, sid in zip(imgs, order):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.shapes.add_picture(str(img), 0, 0, width=prs.slide_width, height=prs.slide_height)
    s.notes_slide.notes_text_frame.text = notas[sid]

cp = prs.core_properties
cp.title = "KNN en paralelo – Exposición final"
cp.author = cp.last_modified_by = "Grupo 7 · CS4052"
cp.subject = "Caso 5: KNN en paralelo con MPI (mpi4py)"
salida = AQUI / "presentacion_final.pptx"
prs.save(salida)

chk = Presentation(salida)
assert len(chk.slides) == len(order)
for s, sid in zip(chk.slides, order):
    pics = [sh for sh in s.shapes if sh.shape_type == 13]
    assert len(pics) == 1 and pics[0].width == chk.slide_width and pics[0].height == chk.slide_height
    assert s.notes_slide.notes_text_frame.text == notas[sid].replace("\r", ""), sid
print("PPTX:", salida, salida.stat().st_size, f"bytes; {len(order)} diapositivas con notas verificadas")
