"""One-off script: render each book PDF under PUSTAK_SOURCE_DIR
(~/Desktop/पुस्तके) into per-page JPEGs under pustak-cache/<book-id>/
(page-0001.jpg, page-0002.jpg, ...) using poppler's pdftoppm CLI tool — no
pip dependency needed (see "No pip/venv" in CLAUDE.md; poppler-utils is
already installed as a system package). app.py never serves the source PDF
itself, only these pre-rendered pages, one at a time, via
/pustak/<id>/page/<n>.jpg.

150 DPI / JPEG quality 78 is a deliberate middle ground: legible for
on-screen reading, well below print quality, so a page-by-page save can't
casually reassemble a high-fidelity copy of the book.

Re-run whenever a book is added/replaced under PUSTAK_SOURCE_DIR. Safe to
re-run any time — each book is rendered into a temp dir first and only
swapped into place once fully rendered.

Usage: python3 build_pustak_cache.py
"""
import os
import re
import shutil
import subprocess
import time

import app

RENDER_DPI = 150
JPEG_QUALITY = 78
RAW_PAGE_RE = re.compile(r"^raw-(\d+)\.jpg$")


def render_book(book):
    source_path = os.path.join(app.PUSTAK_SOURCE_DIR, book["source"])
    if not os.path.isfile(source_path):
        print(f"  SKIP {book['id']}: source not found at {source_path}")
        return

    dest_dir = os.path.join(app.PUSTAK_CACHE_DIR, book["id"])
    tmp_dir = dest_dir + ".tmp"
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)

    start = time.time()
    subprocess.run(
        [
            "pdftoppm", "-jpeg", "-r", str(RENDER_DPI),
            "-jpegopt", f"quality={JPEG_QUALITY}",
            source_path, os.path.join(tmp_dir, "raw"),
        ],
        check=True,
    )

    # pdftoppm names output "raw-<N>.jpg" with a page-count-dependent
    # zero-padding width — extract the number with a regex rather than
    # assuming a fixed width, then re-number to a fixed page-NNNN.jpg so
    # app.py's route never has to guess the padding.
    pages = []
    for f in os.listdir(tmp_dir):
        m = RAW_PAGE_RE.match(f)
        if m:
            pages.append((int(m.group(1)), f))
    pages.sort()
    for i, (_, f) in enumerate(pages, start=1):
        os.rename(os.path.join(tmp_dir, f), os.path.join(tmp_dir, f"page-{i:04d}.jpg"))

    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)
    os.rename(tmp_dir, dest_dir)

    elapsed = time.time() - start
    size_mb = sum(os.path.getsize(os.path.join(dest_dir, f)) for f in os.listdir(dest_dir)) / (1024 * 1024)
    print(f"  {book['id']}: {len(pages)} pages, {size_mb:.1f} MB in {elapsed:.1f}s")


def main():
    os.makedirs(app.PUSTAK_CACHE_DIR, exist_ok=True)
    for book in app.PUSTAK_DEFS:
        print(f"{book['id']}:")
        render_book(book)


if __name__ == "__main__":
    main()
