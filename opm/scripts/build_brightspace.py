"""
Build Brightspace HTML pages by combining Quarto output with HvA huisstijl template.

Converts Quarto's Bootstrap JS tabs to pure CSS radio-button tabs
so they work in Brightspace (which strips <script> tags).

Usage: uv run python scripts/build_brightspace.py

Reads:
  - _site/index.html      (Quarto rendered output — beoordeling)
  - _site/werkwijze.html   (Quarto rendered output — werkwijze)
  - docs/huisstijl.html    (HvA template)

Writes:
  - docs/beoordeling.html
  - docs/werkwijze.html
"""

import base64
import re
from pathlib import Path


CSS_TAB_STYLE = """
<style>
/* CSS-only radio-button tabs */
.sprint-tabs input[type="radio"] { display: none; }
.sprint-tabs .nav-tabs { margin-top: 1.5rem; border-bottom: 2px solid #dee2e6; }
.sprint-tabs .nav-tabs label {
  display: inline-block; padding: 8px 16px; cursor: pointer;
  border: 1px solid transparent; border-bottom: none;
  border-radius: 4px 4px 0 0; background: #f5f5f5; color: #555; margin-bottom: -2px;
}
.sprint-tabs .nav-tabs label:hover { background: #e8e8e8; }
#tab1:checked ~ .nav-tabs label[for="tab1"],
#tab2:checked ~ .nav-tabs label[for="tab2"],
#tab3:checked ~ .nav-tabs label[for="tab3"] {
  background: #fff; border-color: #dee2e6; border-bottom-color: #fff;
  color: #e60073; font-weight: 600;
}
.sprint-tabs .tab-panel { display: none; padding: 1.5rem 0; }
#tab1:checked ~ #content1,
#tab2:checked ~ #content2,
#tab3:checked ~ #content3 { display: block; }

/* Prompt table */
.prompt-table { width: 100%; margin-top: 1rem; font-size: 0.85em; }
.prompt-table th { background: #f5f5f5; }
.prompt-table td:first-child { width: 10%; font-weight: 600; }
.prompt-table td, .prompt-table th { vertical-align: top; }
.prompt-table ol { margin: 0; padding-left: 1.2rem; }
.prompt-table ol li { margin-bottom: .4rem; }

/* Compact ordered lists in tab panels */
.tab-panel ol { margin-top: 0.25rem; margin-bottom: 0.5rem; }
.tab-panel ol li { margin-bottom: 0; }
.tab-panel ol li p { margin-bottom: 0.15rem; }

/* Page metadata footer */
.page-meta { font-size: 0.65em; color: #999; border-top: 1px solid #ddd;
  margin-top: 2rem; padding-top: 0.5rem; }
.page-meta .meta-row { display: flex; justify-content: space-between;
  margin-bottom: 0; line-height: 1.4; }
</style>
"""


CSS_WERKWIJZE_STYLE = """
<style>
.columns { display: flex; gap: 1.5em; }
.column { flex: auto; overflow-x: auto; }
.column img { max-width: 100%; height: auto; }
</style>
"""


def extract_main_content(html: str) -> str:
    """Extract content inside <main>."""
    match = re.search(r"<main[^>]*>(.*?)</main>", html, re.DOTALL)
    if match:
        return match.group(1).strip()
    raise ValueError("Could not find <main> in Quarto output")


def extract_tab_panes(content: str) -> list[tuple[str, str]]:
    """Extract tab labels and their content from Quarto's panel-tabset."""
    # Find tab labels from nav-tabs
    labels = re.findall(r'class="nav-link[^"]*"[^>]*>([^<]+)</a>', content)

    # Find tab pane contents
    panes = re.findall(
        r'<div id="tabset-\d+-\d+"[^>]*>(.*?)</div>\s*(?=<div id="tabset-|\s*</div>\s*</div>)',
        content,
        re.DOTALL,
    )

    return list(zip(labels, panes))


def extract_before_tabs(content: str) -> str:
    """Extract content before the panel-tabset div."""
    match = re.search(r"(.*?)<div[^>]*class=\"tabset-margin-container", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_after_tabs(content: str) -> str:
    """Extract content after the panel-tabset closing divs (page-meta etc)."""
    # Find the closing of the panel-tabset, then get everything after
    match = re.search(r"</div>\s*</div>\s*</div>\s*(<hr>.*)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def build_css_tabs(tabs: list[tuple[str, str]], default_tab: int = 2) -> str:
    """Build CSS radio-button tabs HTML."""
    lines = ['<div class="sprint-tabs">']

    # Radio inputs
    for i, (label, _) in enumerate(tabs, 1):
        checked = " checked" if i == default_tab else ""
        lines.append(f'<input type="radio" name="sprint" id="tab{i}"{checked}>')

    # Tab labels
    lines.append('<div class="nav-tabs">')
    for i, (label, _) in enumerate(tabs, 1):
        lines.append(f'  <label for="tab{i}">{label}</label>')
    lines.append("</div>")

    # Tab content panels
    for i, (_, pane_content) in enumerate(tabs, 1):
        # Clean up Quarto-specific attributes
        cleaned = pane_content.strip()
        cleaned = re.sub(r' class="caption-top table"', ' class="table table-bordered prompt-table"', cleaned)
        cleaned = re.sub(r' data-quarto-table-cell-role="th"', "", cleaned)
        cleaned = re.sub(r' class="(odd|even|header)"', "", cleaned)
        lines.append(f'<div id="content{i}" class="tab-panel">')
        lines.append(cleaned)
        lines.append("</div>")

    lines.append("</div>")
    return "\n".join(lines)


def strip_quarto_header(content: str) -> str:
    """Remove the Quarto title-block-header, keep just the h1 title."""
    # Extract just the title text
    title_match = re.search(r'<h1 class="title">([^<]+)</h1>', content)
    title = title_match.group(0) if title_match else ""

    # Remove the entire header block
    content = re.sub(
        r'<header id="title-block-header".*?</header>',
        title,
        content,
        flags=re.DOTALL,
    )
    return content


def inject_into_huisstijl(huisstijl: str, title: str, content: str, extra_head: str = "") -> str:
    """Inject content into the HvA huisstijl template."""
    page = huisstijl

    # Replace title
    page = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", page)

    # Inject extra styles before </head>
    if extra_head:
        page = page.replace("</head>", f"{extra_head}\n</head>")

    # Replace the content area
    placeholder_pattern = re.compile(
        r'(<div class="col-xs-12 col-sm-offset-2 col-sm-8">).*?(</div>\s*</div>\s*<footer>)',
        re.DOTALL,
    )
    page = placeholder_pattern.sub(rf"\1\n{content}\n\2", page)
    return page


def build_brightspace():
    root = Path(__file__).resolve().parent.parent
    quarto_html = (root / "_site" / "index.html").read_text(encoding="utf-8")
    huisstijl = (root / "docs" / "huisstijl.html").read_text(encoding="utf-8")

    # Extract main content from Quarto output
    main_content = extract_main_content(quarto_html)
    main_content = strip_quarto_header(main_content)

    # Extract parts
    before_tabs = extract_before_tabs(main_content)
    tabs = extract_tab_panes(main_content)
    after_tabs = extract_after_tabs(main_content)

    # Build the page content with CSS tabs
    css_tabs = build_css_tabs(tabs, default_tab=2)
    page_content = f"{before_tabs}\n\n{css_tabs}\n\n{after_tabs}"

    page = inject_into_huisstijl(
        huisstijl,
        title="Beoordelingsprompts — Docentinstructie",
        content=page_content,
        extra_head=CSS_TAB_STYLE,
    )

    output_path = root / "docs" / "beoordeling.html"
    output_path.write_text(page, encoding="utf-8")
    print(f"Generated: {output_path}")


def embed_local_images(content: str, base_dir: Path) -> str:
    """Replace local image src with inline base64 data URIs."""

    def _replace(match: re.Match) -> str:
        src = match.group(1)
        img_path = base_dir / src
        if img_path.exists():
            data = base64.b64encode(img_path.read_bytes()).decode()
            suffix = img_path.suffix.lstrip(".")
            mime = f"image/{suffix}"
            return f'src="data:{mime};base64,{data}"'
        return match.group(0)

    return re.sub(r'src="([^"]+\.(?:png|jpg|svg))"', _replace, content)


def fix_mermaid_svg(content: str) -> str:
    """Remove fixed width/height from mermaid SVGs so viewBox controls scaling."""
    content = re.sub(
        r'(<svg[^>]*class="flowchart"[^>]*) width="\d+"',
        r'\1 width="100%"',
        content,
    )
    content = re.sub(
        r'(<svg[^>]*class="flowchart"[^>]*) height="\d+"',
        r"\1",
        content,
    )
    return content


def build_werkwijze():
    root = Path(__file__).resolve().parent.parent
    quarto_html = (root / "_site" / "werkwijze.html").read_text(encoding="utf-8")
    huisstijl = (root / "docs" / "huisstijl.html").read_text(encoding="utf-8")

    # Extract main content
    main_content = extract_main_content(quarto_html)
    main_content = strip_quarto_header(main_content)
    # Remove h1 title to avoid duplication with Brightspace page name
    main_content = re.sub(r'<h1 class="title">[^<]+</h1>', "", main_content)
    main_content = embed_local_images(main_content, root / "_site")

    page = inject_into_huisstijl(
        huisstijl,
        title="Werkwijze — Docentinstructie",
        content=main_content,
        extra_head=CSS_WERKWIJZE_STYLE,
    )

    output_path = root / "docs" / "werkwijze.html"
    output_path.write_text(page, encoding="utf-8")
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    build_brightspace()
    build_werkwijze()
