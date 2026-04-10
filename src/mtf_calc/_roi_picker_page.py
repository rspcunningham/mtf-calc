from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_roi_picker_html() -> str:
    ui_dir = Path(__file__).with_name("ui")
    html = (ui_dir / "roi_picker.html").read_text(encoding="utf-8")
    css = (ui_dir / "roi_picker.css").read_text(encoding="utf-8")
    js = (ui_dir / "roi_picker.js").read_text(encoding="utf-8")

    html = html.replace(
        '<link rel="stylesheet" href="./roi_picker.css">',
        f"<style>\n{css}\n</style>",
    )
    html = html.replace(
        '<script type="module" src="./roi_picker.js"></script>',
        f"<script type=\"module\">\n{js}\n</script>",
    )
    return html
