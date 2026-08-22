# Résumé & Portfolio Pipeline

One YAML file is the source of truth. One command produces two deliverables:

| Output | What it is | Audience |
| --- | --- | --- |
| `dist/Abhishek_Mishra_Resume.pdf` | Single-page, single-column, ATS-parse-safe résumé | Recruiters, applicant tracking systems |
| `dist/index.html` | Self-contained animated portfolio page (77 KB, no external assets except two Google Fonts) | Embedded in Google Sites / served from GitHub Pages |

Both are rendered from [resume_data.yaml](resume_data.yaml). Edit the YAML, rebuild, and the two stay in sync by construction.

## Build

```bash
pip install -r requirements.txt && python -m playwright install chromium
```

```bash
python build_resume.py
```

Flags (mutually exclusive):

```bash
python build_resume.py --pdf-only
```

```bash
python build_resume.py --portfolio-only
```

Deploying the result: see [DEPLOY.md](DEPLOY.md).

## Layout

```
resume_data.yaml          the only place content lives
build_resume.py           loads YAML -> renders Jinja -> prints PDF via Playwright
templates/
  resume_pdf.html         PDF markup      -- single column, no tables
  resume_pdf.css          PDF styling     -- owns @page geometry
  portfolio_page.html     web markup      -- inlines the two files below
  portfolio_page.css      web styling     -- aurora, starfield, tilt, shine, reveal
  portfolio_page.js       web behaviour   -- reveal, tilt, counters, filters
dist/
  Abhishek_Mishra_Resume.pdf
  index.html
  resume.html             intermediate the PDF is printed from; harmless to serve
  .nojekyll               stops GitHub Pages from running Jekyll over dist/
```

## Invariants

Four rules hold this together. Breaking any of them is a real regression, not a style nit.

**1. The PDF is exactly one page.** `build_resume.py` counts `/Count` in the PDF trailer after printing and exits `1` if the total is not 1. A failing build is the intended behaviour — it means content was added without trimming something else. `resume_data.yaml` carries an inline warning that a 6th `core_skills` category will overflow.

**2. Page geometry lives only in CSS.** `generate_pdf()` calls Playwright with `prefer_css_page_size=True` and passes no `margin`, so `@page { size: A4 portrait; margin: 9mm 13mm; }` in `resume_pdf.css` is the single source of truth. Setting margins in Python as well produces silent double-margins.

**3. Included asset files are parsed by Jinja.** `portfolio_page.css` and `portfolio_page.js` are pulled in with `{% include %}`, so Jinja lexes them. A doubled opening brace, a brace-percent pair, or a brace-hash pair anywhere in those files — *including inside comments* — kills the build. Both files carry this warning in their header. To check after editing:

```bash
grep -nE '\{\{|\{%|\{#' templates/portfolio_page.css templates/portfolio_page.js
```

**4. The web page covers the whole YAML.** The PDF is deliberately selective (3 flagship projects as one-liners plus the portfolio URL); the page is not. Current coverage, verified by querying the rendered DOM rather than by assertion: 9 project cards, 5 skill cards, 9 experience bullets, 18 metric chips. Adding a YAML field means adding it to `portfolio_page.html`. The one intentional omission is `contact.portfolio_url`, since the page *is* that URL.

## Things that will bite you

- **`StrictUndefined` is on.** Referencing a key the YAML does not have raises at render time instead of quietly producing an empty string. That is the point — but it means new template variables must also be injected in `build_resume.py` (as `pdf_name` is) or added to the YAML.
- **`auto-fit` grid tracks cannot shrink below a fixed minimum.** `minmax(440px, 1fr)` overflows any viewport narrower than 440px. All four grids in `portfolio_page.css` use `minmax(min(Npx, 100%), 1fr)` for this reason. Reintroducing the bare pixel form brings back horizontal scroll on phones.
- **`IntersectionObserver` alone is not enough for scroll reveal.** A fast wheel flick or an anchor jump can carry an element past the viewport between two observer evaluations, and the failure mode is content that is invisible *permanently*. `initReveal()` pairs the observer with a rAF-throttled scroll sweep that force-reveals anything already in or past view.
- **Counters must skip ranges.** `"1-2%"` matches a leading-number regex and would animate through `"0-2%"`. `initCounters()` bails on any value containing a digit-dash-digit.
- **Google Sites sandboxes the embed.** Nothing on the page persists state, and the résumé download link carries `target="_blank"` so a sandbox that blocks downloads still surfaces the PDF. See [DEPLOY.md](DEPLOY.md).

## Verified state

Last full pass:

```
python build_resume.py   -> PDF 1 page, 203 KB; index.html 77 KB self-contained
desktop 1440px           -> 10,310px tall, no console errors
mobile 390px             -> 18,995px tall, no console errors, no horizontal overflow
reduced-motion           -> all content visible, no tilt transform
iframe embed             -> all 9 cards render, all reveals resolve on inner scroll
```
