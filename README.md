# Résumé & Portfolio Pipeline

One YAML file is the source of truth. One command produces two deliverables:

| Output | What it is | Audience |
| --- | --- | --- |
| `dist/Abhishek_Mishra_Resume.pdf` | Single-page, single-column, ATS-parse-safe résumé | Recruiters, applicant tracking systems |
| `dist/index.html` | Self-contained tabbed portfolio page (91 KB, no external assets except two Google Fonts) | Embedded in Google Sites / served from GitHub Pages |

Both are rendered from [resume_data.yaml](resume_data.yaml). Edit the YAML, rebuild, and the two stay in sync by construction.

Live: <https://abhishm23.github.io/portfolio/>

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

Then check the page still behaves — 44 assertions, exits non-zero on any failure:

```bash
python tests/verify_portfolio.py
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
  portfolio_page.js       web behaviour   -- tabs, reveal, tilt, counters, sub-tabs
tests/
  verify_portfolio.py     drives dist/index.html in headless Chromium; 44 checks
  measure_heights.py      per-tab height table at the widths an embed can take
dist/
  Abhishek_Mishra_Resume.pdf
  index.html
  resume.html             intermediate the PDF is printed from; git-ignored
  .nojekyll               stops GitHub Pages from running Jekyll over dist/
```

`dist/` is committed on purpose: it is what gets published to the `gh-pages` branch.

## The page is tabbed, and that is load-bearing

A Google Sites embed gets a **fixed** height and never auto-resizes, so a single
10,000px scrolling page would show a tenth of itself at a time. The content is
therefore split across six ARIA tab panels — Profile, Capabilities, Experience,
Selected Work, Credentials, Contact — which brings the tallest view down to
roughly one frame.

Three things follow from that design and are easy to break:

- **Hiding is the script's job, never the markup's.** `portfolio_page.html` ships
  with no `hidden` attribute on any panel. `initTabs()` adds them. So a total JS
  failure degrades to the old long scrolling page — every word still readable —
  rather than a blank frame. Do not author `hidden` into the template.
- **A panel switch has to re-run the reveal sweep.** An element observed while
  its panel is `display:none` reports zero intersection *forever after*. That is
  why `initReveal()` exports `refreshReveal()` and why `activate()` and the
  Selected Work sub-tabs both call it.
- **The sweep must skip zero-size rects.** Two of the three Work pillars are
  hidden at any time, so their cards measure `0×0` at the origin and would
  otherwise satisfy "top is above the fold" and reveal with no stagger.

### URL contract

| URL | Effect |
| --- | --- |
| `index.html` | Full page, Profile tab active |
| `index.html?tab=work` | Full page, Selected Work active |
| `index.html#credentials` | Same, via hash (`?tab=` wins if both are present) |
| `index.html?solo=1&tab=experience` | **One panel alone** — masthead, tab bar and footer removed |

`?solo=1` is what makes "embed the sections one at a time" possible without
building six files: point six separate Sites embeds at the same URL with
different `tab=` values. Valid keys are the `data-tab` values in the template:
`profile`, `capabilities`, `experience`, `work`, `credentials`, `contact`. An
unknown key falls back to Profile rather than rendering nothing.

The active tab is written back to the URL with `replaceState`, never
`pushState` — inside an iframe, pushing history entries hijacks the host page's
Back button.

## Invariants

Four rules hold this together. Breaking any of them is a real regression, not a style nit.

**1. The PDF is exactly one page.** `build_resume.py` counts `/Count` in the PDF trailer after printing and exits `1` if the total is not 1. A failing build is the intended behaviour — it means content was added without trimming something else. `resume_data.yaml` carries an inline warning that a 6th `core_skills` category will overflow.

**2. Page geometry lives only in CSS.** `generate_pdf()` calls Playwright with `prefer_css_page_size=True` and passes no `margin`, so `@page { size: A4 portrait; margin: 9mm 13mm; }` in `resume_pdf.css` is the single source of truth. Setting margins in Python as well produces silent double-margins.

**3. Included asset files are parsed by Jinja.** `portfolio_page.css` and `portfolio_page.js` are pulled in with `{% include %}`, so Jinja lexes them. A doubled opening brace, a brace-percent pair, or a brace-hash pair anywhere in those files — *including inside comments* — kills the build. Both files carry this warning in their header. To check after editing:

```bash
grep -nE '\{\{|\{%|\{#' templates/portfolio_page.css templates/portfolio_page.js
```

**4. The web page covers the whole YAML.** The PDF is deliberately selective (3 flagship projects as one-liners plus the portfolio URL); the page is not. Current coverage, verified by querying the rendered DOM rather than by assertion: 9 project cards, 5 skill cards, 9 experience bullets, 18 metric chips, 3 flagship tags. Adding a YAML field means adding it to `portfolio_page.html`. The one intentional omission is `contact.portfolio_url`, since the page *is* that URL.

## Things that will bite you

- **`StrictUndefined` is on.** Referencing a key the YAML does not have raises at render time instead of quietly producing an empty string. That is the point — but it means new template variables must also be injected in `build_resume.py` (as `pdf_name` is) or added to the YAML.
- **`auto-fit` grid tracks cannot shrink below a fixed minimum.** `minmax(440px, 1fr)` overflows any viewport narrower than 440px. All four grids in `portfolio_page.css` use `minmax(min(Npx, 100%), 1fr)` for this reason. Reintroducing the bare pixel form brings back horizontal scroll on phones.
- **`IntersectionObserver` alone is not enough for scroll reveal.** A fast wheel flick, an anchor jump, or a `display:none` panel can leave an element invisible *permanently*. `initReveal()` pairs the observer with a rAF-throttled scroll sweep that force-reveals anything already in or past view.
- **Counters must skip ranges.** `"1-2%"` matches a leading-number regex and would animate through `"0-2%"`. `initCounters()` bails on any value containing a digit-dash-digit.
- **Google Sites sandboxes the embed.** Nothing on the page persists state, and the résumé download link carries `target="_blank"` so a sandbox that blocks downloads still surfaces the PDF. See [DEPLOY.md](DEPLOY.md).

## Verified state

Last full pass:

```
python build_resume.py         -> PDF 1 page, 203 KB; index.html 91 KB self-contained
python tests/verify_portfolio.py -> 44 passed, 0 failed, no console errors

tallest panel      1440px  3,258px (Selected Work, all 9 cards)
                   1030px  3,398px      <- Google Sites full-width section
                    390px  6,025px
shortest panel     1030px    900px (Credentials)
no horizontal overflow at 390 / 640 / 768 / 1030 / 1440px

reduced-motion     all content visible, no tilt transform, no panel animation
live Pages URL     fonts load, PDF link resolves under /portfolio/, 0 errors
```

---

## 🛠️ Tech Stack & Open Source Credits

- **[Jinja2](https://palletsprojects.com/p/jinja/)** — High-performance Python templating engine.
- **[Playwright](https://playwright.dev/)** — Headless browser execution for deterministic PDF generation.
- **[PyYAML](https://pyyaml.org/)** — Strict YAML parsing for single-source-of-truth configuration.
- **[Google Fonts (Inter & Space Grotesk)](https://fonts.google.com/)** — Typography design.

---

## 👥 Authors & Contributors

- **Author:** [Abhishek Mishra](https://github.com/abhishm23) — *Senior Analytics & GenAI Engineer*
- **Co-Developer / AI Pair Programmer:** [Google Antigravity](https://antigravity.google/)

