"""Turn a rendered WARFRAME Wiki article (HTML) into clean Markdown-ish text for embedding.

Kept: headings, paragraphs, lists, the infobox (as "Label: value" lines) and tables (as "a | b | c" rows),
because many stats only exist in the rendered infobox and tables.
Dropped: navboxes, edit links, references, table of contents, images, and sections that are noise
for question answering (see SKIP_SECTIONS).
"""
import re

from bs4 import BeautifulSoup, NavigableString, Tag

# Elements removed before converting. Navboxes are repeated on hundreds of pages and would
# otherwise dominate retrieval results.
DROP_SELECTORS = [
    "script", "style", "noscript", "img", "figure", "audio", "video",
    ".navbox", "[class*=NavBox]", ".mw-editsection", ".toc", "#toc", ".noprint",
    "sup.reference", ".mw-references-wrap", "ol.references", ".gallery",
    ".article-tabs", ".tabber__header", "[class*=button-c-pre]", ".mw-empty-elt",
]

# Section headings whose whole section is dropped (case-insensitive).
SKIP_SECTIONS = {"see also", "references", "patch history", "localization", "navigation", "media", "gallery"}

HEADINGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}


def _text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _table(table):
    rows = []
    for tr in table.find_all("tr"):
        if tr.find_parent("table") is not table:
            continue  # nested tables are handled through their cell text
        cells = [_text(c) for c in tr.find_all(["th", "td"], recursive=False)]
        cells = [c for c in cells if c]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _infobox(box):
    lines = []
    title = box.select_one(".title")
    if title:
        lines.append(f"Infobox: {_text(title)}")
    skipping = False
    for el in box.select(".header, .row"):
        if "header" in el.get("class", []):
            # Editor tools and an external link, not game info.
            skipping = _text(el) in ("Maintenance", "Official Drop Tables")
            if not skipping:
                lines.append(f"[{_text(el)}]")
            continue
        if skipping:
            continue
        label, value = el.select_one(".label"), el.select_one(".value")
        if label and value:
            lines.append(f"{_text(label)}: {_text(value)}")
        elif _text(el):
            lines.append(_text(el))
    return "\n".join(lines)


def _blocks(node):
    """Yield text blocks from node's children in document order."""
    for child in node.children:
        if isinstance(child, NavigableString):
            text = re.sub(r"\s+", " ", str(child)).strip()
            if text:
                yield text
            continue
        if not isinstance(child, Tag):
            continue
        classes = child.get("class", [])
        name = child.name
        if "infobox" in classes:
            yield _infobox(child)
        elif "mw-heading" in classes:
            h = child.find(list(HEADINGS))
            if h:
                yield f"{HEADINGS[h.name]} {_text(h)}"
        elif name in HEADINGS:
            yield f"{HEADINGS[name]} {_text(child)}"
        elif name == "table":
            yield _table(child)
        elif name in ("ul", "ol"):
            items = [_text(li) for li in child.find_all("li", recursive=False)]
            yield "\n".join(f"- {i}" for i in items if i)
        elif name == "dl":
            yield "\n".join(_text(d) for d in child.find_all(["dt", "dd"]) if _text(d))
        elif name in ("p", "blockquote", "pre"):
            yield _text(child)
        elif name in ("div", "section", "span", "center", "dd"):
            yield from _blocks(child)
        else:
            yield _text(child)


def _is_junk(block):
    """Editor-only leftovers: tab edit links and raw JSON data dumps used by the infobox."""
    return block in ("Edit Tab", "CODEX") or (block.startswith("{\"") and block.endswith("}"))


def _drop_skipped_sections(lines):
    out, skipping_level = [], None
    for line in lines:
        m = re.match(r"^(#+) (.*)", line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip().lower()
            if skipping_level is not None and level <= skipping_level:
                skipping_level = None
            if skipping_level is None and title in SKIP_SECTIONS:
                skipping_level = level
        if skipping_level is None:
            out.append(line)
    return out


def html_to_text(html):
    """Return (clean_text, info) for a full article page. info holds revision/last_edited when found."""
    soup = BeautifulSoup(html, "html.parser")
    info = {}
    m = re.search(r'"wgCurRevisionId":(\d+)', html)
    if m:
        info["revision"] = int(m.group(1))
    lastmod = soup.select_one("#footer-info-lastmod")
    if lastmod:
        info["last_edited"] = _text(lastmod).replace("This page was last edited on ", "").rstrip(".")

    body = soup.select_one(".mw-parser-output") or soup.select_one("#mw-content-text")
    if body is None:
        return "", info
    for sel in DROP_SELECTORS:
        for el in body.select(sel):
            el.decompose()

    blocks = [b.strip() for b in _blocks(body)]
    blocks = [b for b in blocks if b and not _is_junk(b)]
    lines = _drop_skipped_sections(blocks)
    text = "\n\n".join(lines)
    text = re.sub(r" ?📝[^\n|]*", "", text)  # "📝 Edit blueprint requirements" style editor links
    return re.sub(r"\n{3,}", "\n\n", text).strip(), info
