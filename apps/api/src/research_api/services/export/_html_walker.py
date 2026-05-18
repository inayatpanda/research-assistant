"""Minimal allow-list HTML walker for DOCX/PDF rendering.

Produces a flat stream of structural events that the renderer can consume:
  - ("paragraph_start",)            — open a new paragraph context
  - ("paragraph_end",)               — close it
  - ("text", str, set[str])          — text run with active inline styles
                                       (subset of {'bold', 'italic', 'sup', 'cite'})
  - ("table_start",)
  - ("row_start",), ("row_end",)
  - ("cell_start", bool)             — bool is is_header
  - ("cell_end",)
  - ("table_end",)
  - ("svg_img", str)                 — data-URI of an embedded image
  - ("heading", int, str)            — local heading level + text (rare; for h1-h3 inside content)

The walker is deliberately permissive: unknown tags are passed through (their
text content surfaces) and script/style tags drop their contents.
"""
from __future__ import annotations

from html.parser import HTMLParser
from typing import Iterator


_INLINE_TAGS = {"strong", "b", "em", "i", "sup", "u"}
_DROP_TAGS = {"script", "style", "head", "meta", "link"}
_BLOCK_TAGS = {"p", "div", "section", "article", "blockquote", "li"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4"}


def _attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for k, v in attrs:
        if k == name:
            return v
    return None


class _Walker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple] = []
        self.style_stack: list[str] = []
        self.cite_stack: list[str | None] = []  # article_id when inside a citation sup
        self.drop_depth = 0
        self.in_paragraph = False
        self.in_table = False
        self.in_cell = False
        self.cell_is_header = False

    def _styles(self) -> set[str]:
        return set(self.style_stack)

    def _ensure_paragraph_open(self) -> None:
        if not self.in_paragraph and not self.in_cell:
            self.events.append(("paragraph_start",))
            self.in_paragraph = True

    def _close_paragraph(self) -> None:
        if self.in_paragraph:
            self.events.append(("paragraph_end",))
            self.in_paragraph = False

    def handle_starttag(self, tag, attrs):
        if self.drop_depth > 0 or tag in _DROP_TAGS:
            self.drop_depth += 1
            return

        if tag == "img":
            src = _attr(attrs, "src") or ""
            if src.startswith("data:image/svg+xml"):
                # Close any open paragraph first.
                self._close_paragraph()
                self.events.append(("svg_img", src))
            return

        if tag == "br":
            if self.in_paragraph or self.in_cell:
                self.events.append(("text", "\n", self._styles()))
            return

        if tag in _BLOCK_TAGS:
            self._close_paragraph()
            self.events.append(("paragraph_start",))
            self.in_paragraph = True
            return

        if tag in _HEADING_TAGS:
            self._close_paragraph()
            level = int(tag[1])
            self.events.append(("heading_start", level))
            self.in_paragraph = True
            return

        if tag == "table":
            self._close_paragraph()
            self.events.append(("table_start",))
            self.in_table = True
            return

        if tag in ("thead", "tbody", "tfoot"):
            return

        if tag == "tr":
            self.events.append(("row_start",))
            return

        if tag in ("td", "th"):
            self.cell_is_header = tag == "th"
            self.events.append(("cell_start", self.cell_is_header))
            self.in_cell = True
            return

        if tag in _INLINE_TAGS:
            # Map tag to canonical style name.
            style = {"b": "bold", "strong": "bold", "i": "italic", "em": "italic",
                     "sup": "sup", "u": "underline"}[tag]
            self.style_stack.append(style)
            # Detect citation sup.
            if tag == "sup":
                aid = _attr(attrs, "data-article-id")
                self.cite_stack.append(aid)
            return

        # Unknown tag: ignored, but its text content will flow through.

    def handle_endtag(self, tag):
        if self.drop_depth > 0:
            if tag in _DROP_TAGS:
                self.drop_depth -= 1
            else:
                self.drop_depth -= 0  # extraneous closer for an open drop, ignore
            return

        if tag in _BLOCK_TAGS:
            self._close_paragraph()
            return

        if tag in _HEADING_TAGS:
            if self.in_paragraph:
                self.events.append(("heading_end",))
                self.in_paragraph = False
            return

        if tag == "table":
            self.events.append(("table_end",))
            self.in_table = False
            return

        if tag == "tr":
            self.events.append(("row_end",))
            return

        if tag in ("td", "th"):
            self.events.append(("cell_end",))
            self.in_cell = False
            self.cell_is_header = False
            return

        if tag in _INLINE_TAGS:
            if self.style_stack:
                # Pop the matching style — best-effort: pop the topmost.
                style = {"b": "bold", "strong": "bold", "i": "italic", "em": "italic",
                         "sup": "sup", "u": "underline"}[tag]
                # Remove latest occurrence.
                for i in range(len(self.style_stack) - 1, -1, -1):
                    if self.style_stack[i] == style:
                        del self.style_stack[i]
                        break
            if tag == "sup" and self.cite_stack:
                self.cite_stack.pop()
            return

    def handle_data(self, data):
        if self.drop_depth > 0:
            return
        if not data:
            return
        if self.in_cell:
            self.events.append(("text", data, self._styles()))
            return
        if self.in_paragraph:
            self.events.append(("text", data, self._styles()))
            return
        text = data.strip()
        if text:
            self._ensure_paragraph_open()
            self.events.append(("text", data, self._styles()))


def walk_html(html: str) -> list[tuple]:
    """Parse `html` and return the structural event stream.

    Robust to malformed input — `html.parser.HTMLParser` is lenient. Returns
    an empty list for `None`/empty input.
    """
    if not html:
        return []
    w = _Walker()
    w.feed(html)
    w._close_paragraph()
    return w.events
