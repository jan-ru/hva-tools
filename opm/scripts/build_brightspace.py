"""
Build brightspace.html by combining Quarto output with HvA huisstijl template.

Usage: uv run python scripts/build_brightspace.py

Reads:
  - _site/index.html  (Quarto rendered output)
  - docs/huisstijl.html (HvA template)

Writes:
  - docs/brightspace.html
"""

import re
from pathlib import Path


def extract_body_content(html: str) -> str:
    """Extract content between the main heading and the end of the Quarto content."""
    # Find everything inside <main> or the quarto content div
    # Quarto wraps content in <main class="content" ...> or <div id="quarto-content">
    match = re.search(
        r'<main[^>]*>(.*?)</main>',
        html,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()

    # Fallback: extract body content
    match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if match:
        return match.group(1).strip()

    raise ValueError("Could not extract content from Quarto output")


def extract_quarto_styles(html: str) -> str:
    """Extract any inline <style> blocks from Quarto output."""
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    return '\n'.join(styles)


def build_brightspace():
    root = Path(__file__).resolve().parent.parent
    quarto_html = (root / "_site" / "index.html").read_text(encoding="utf-8")
    huisstijl = (root / "docs" / "huisstijl.html").read_text(encoding="utf-8")

    # Extract content and styles from Quarto output
    content = extract_body_content(quarto_html)
    extra_styles = extract_quarto_styles(quarto_html)

    # Build the HvA-styled page
    # Replace the placeholder content in huisstijl.html
    page = huisstijl

    # Replace title
    page = re.sub(r'<title>.*?</title>', '<title>Beoordelingsprompts — Docentinstructie</title>', page)

    # Replace the content area
    placeholder_pattern = re.compile(
        r'(<div class="col-xs-12 col-sm-offset-2 col-sm-8">).*?(</div>\s*</div>\s*<footer>)',
        re.DOTALL,
    )
    replacement = rf'\1\n{content}\n\2'
    page = placeholder_pattern.sub(replacement, page)

    # Inject extra styles if any
    if extra_styles:
        style_block = f'<style>\n{extra_styles}\n</style>'
        page = page.replace('</head>', f'{style_block}\n</head>')

    output_path = root / "docs" / "brightspace.html"
    output_path.write_text(page, encoding="utf-8")
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    build_brightspace()
