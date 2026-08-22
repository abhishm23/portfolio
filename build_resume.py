"""
build_resume.py — renders resume_data.yaml into two deliverables.

Outputs (all in dist/):
    Abhishek_Mishra_Resume.pdf   1-page, ATS-safe, single-column resume
    resume.html                  intermediate the PDF is printed from (kept for debugging)
    index.html                   self-contained animated portfolio page
    .nojekyll                    lets GitHub Pages serve the files verbatim

Design notes (these fix real bugs, please don't undo them):

  * Every path resolves off __file__, not the working directory, so the script
    runs correctly from anywhere.
  * dist/ is created if missing.
  * --pdf-only and --portfolio-only are mutually exclusive; passing both used to
    silently produce nothing.
  * Page margins are declared ONCE, in the @page rule inside resume_pdf.css.
    Playwright is told prefer_css_page_size=True and is NOT passed a margin
    argument — previously both defined margins and Chromium's resolution
    between them was ambiguous.
  * Templates inline their own CSS/JS via Jinja {% include %}, so the rendered
    HTML is self-contained. This removes the shutil CSS-copy step and the
    file:// relative-path fragility that came with it, and is what makes
    dist/index.html embeddable as a single file.
"""

import argparse
import asyncio
import os
import re
import sys

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from playwright.async_api import async_playwright

# --- Paths are anchored to this file, never to the CWD. ----------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(ROOT, "templates")
DIST_DIR = os.path.join(ROOT, "dist")
DATA_FILE = os.path.join(ROOT, "resume_data.yaml")

PDF_NAME = "Abhishek_Mishra_Resume.pdf"


def load_data(path=DATA_FILE):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def make_env():
    # StrictUndefined turns a typo'd variable into a loud error instead of
    # silently rendering an empty string into the resume.
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(env, data, template_name, output_name):
    template = env.get_template(template_name)
    html = template.render(**data)

    output_path = os.path.join(DIST_DIR, output_name)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path


def pdf_page_count(pdf_path):
    """Page count straight out of the PDF page tree.

    Avoids adding a pypdf dependency for one integer. The root /Pages node
    carries the total, so the largest /Count in the file is the page count.
    """
    with open(pdf_path, "rb") as fh:
        raw = fh.read()
    counts = [int(n) for n in re.findall(rb"/Count\s+(\d+)", raw)]
    return max(counts) if counts else 0


async def generate_pdf(html_path, pdf_path):
    file_url = "file:///" + os.path.abspath(html_path).replace(os.sep, "/").lstrip("/")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(file_url, wait_until="networkidle")
        # Give webfonts a beat to settle; metrics shift if we print mid-swap.
        try:
            await page.evaluate("document.fonts && document.fonts.ready")
        except Exception:
            pass
        await page.pdf(
            path=os.path.abspath(pdf_path),
            print_background=True,
            prefer_css_page_size=True,  # honour @page in resume_pdf.css
        )
        await browser.close()


def build_resume(env, data):
    print("Rendering resume HTML...")
    html_path = render_html(env, data, "resume_pdf.html", "resume.html")

    print("Printing PDF via headless Chromium...")
    pdf_path = os.path.join(DIST_DIR, PDF_NAME)
    asyncio.run(generate_pdf(html_path, pdf_path))

    pages = pdf_page_count(pdf_path)
    size_kb = os.path.getsize(pdf_path) / 1024
    print(f"  -> {pdf_path}  ({pages} page{'s' if pages != 1 else ''}, {size_kb:.0f} KB)")

    if pages != 1:
        print(
            f"  WARNING: resume is {pages} pages, target is 1.\n"
            f"           Tighten templates/resume_pdf.css (--fs-body, --lh, section gaps)\n"
            f"           or trim content in resume_data.yaml.",
            file=sys.stderr,
        )
    return pages


def build_portfolio(env, data):
    print("Rendering portfolio page...")
    # PDF_NAME is injected so the page's download link and the actual filename
    # can never drift apart.
    context = dict(data, pdf_name=PDF_NAME)
    path = render_html(env, context, "portfolio_page.html", "index.html")
    size_kb = os.path.getsize(path) / 1024
    print(f"  -> {path}  (self-contained, {size_kb:.0f} KB)")

    # GitHub Pages otherwise runs the output through Jekyll.
    nojekyll = os.path.join(DIST_DIR, ".nojekyll")
    if not os.path.exists(nojekyll):
        open(nojekyll, "w").close()
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Generate the 1-page PDF resume and the portfolio page from resume_data.yaml."
    )
    # Mutually exclusive: passing both flags previously generated nothing at all.
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--pdf-only", action="store_true", help="build only the PDF resume")
    target.add_argument("--portfolio-only", action="store_true", help="build only the portfolio page")
    args = parser.parse_args()

    os.makedirs(DIST_DIR, exist_ok=True)

    print(f"Loading {os.path.relpath(DATA_FILE, ROOT)}...")
    data = load_data()
    env = make_env()

    pages = None
    if not args.portfolio_only:
        pages = build_resume(env, data)
    if not args.pdf_only:
        build_portfolio(env, data)

    print("\nDone.")
    if pages is not None and pages != 1:
        sys.exit(1)  # non-zero so a bad page count is visible in CI / scripts


if __name__ == "__main__":
    main()
