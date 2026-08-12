"""One-off script: pre-build every book/chapter ZIP download into
zip-cache/, so app.py can serve them straight from disk with a real
Content-Length (exact file size shown in the browser's download UI)
instead of streaming-building them live with no size known upfront.

Re-run this whenever audio content under AUDIO_DIR changes (new episodes,
renames, etc.) — app.py falls back to the old live-streaming build for any
book/chapter not found in the cache, so it's always safe to run this late
or skip it; nothing breaks, downloads just won't show a size until the
cache is (re)built.

Usage: python3 build_zip_cache.py
"""
import os
import time
import zipfile

import app


def build_one(path, items, label):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    start = time.time()
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_STORED) as zf:
        for arcname, filepath in items:
            zf.write(filepath, arcname=arcname)
    os.replace(tmp_path, path)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  {label}: {size_mb:.1f} MB in {time.time() - start:.1f}s")


def chapter_slug(key):
    if key == "other" or key in app.SPECIAL_CHAPTER_LABELS:
        return key
    return str(key)


def main():
    for book in app.BOOK_DEFS:
        book_id = book["id"]
        print(f"{book_id}:")

        display_name, items = app.build_book_zip_items(book_id)
        build_one(os.path.join(app.ZIP_CACHE_DIR, "book", f"{book_id}.zip"), items, "(whole book)")

        lib = app.LIBRARY[book_id]
        for key in lib["order"]:
            slug = chapter_slug(key)
            display_name, items = app.build_chapter_zip_items(book_id, slug)
            build_one(os.path.join(app.ZIP_CACHE_DIR, "book", book_id, f"{slug}.zip"), items, slug)


if __name__ == "__main__":
    main()
