# Deploying the portfolio page

`dist/index.html` is a single self-contained file. Anything that can serve one
static HTML file over HTTPS can host it.

**Step 1 is already done.** The repo exists, both branches are pushed, and Pages
is live. Step 1 is kept as a record of how, and of how to publish updates.

---

## 1. GitHub Pages — done

Repo: <https://github.com/abhishm23/portfolio> (public — Pages needs public
unless you have a paid plan)

| Branch | Contains | Purpose |
| --- | --- | --- |
| `main` | Everything — YAML, templates, build script, tests | The source |
| `gh-pages` | The contents of `dist/` at the root | What Pages serves |

Live URLs:

```
https://abhishm23.github.io/portfolio/
https://abhishm23.github.io/portfolio/Abhishek_Mishra_Resume.pdf
```

Pages is configured to deploy from branch `gh-pages`, path `/` (root). GitHub
turned Pages on automatically when the `gh-pages` branch first appeared; the
equivalent manual route is **Settings → Pages → Source: Deploy from a branch →
`gh-pages` / `(root)`**.

`build_resume.py` writes `dist/.nojekyll`, which tells Pages to serve the
directory verbatim instead of running it through Jekyll.

### Publishing an update

Edit `resume_data.yaml`, then:

```bash
python build_resume.py && python tests/verify_portfolio.py
```

```bash
git add -A && git commit -m "Update content" && git push
```

```bash
git subtree push --prefix dist origin gh-pages
```

Two things to know:

- **The `git subtree push` line is not optional.** A plain `git push` updates
  `main` only, and `main` is not what Pages serves. Forgetting the subtree push
  is the single most likely reason a change does not appear.
- **Authentication.** The remote is stored without any credential in it. The
  first push after the setup token is revoked will prompt for login — let the
  Windows Git Credential Manager open a browser and sign in to GitHub there.
  That stores a proper credential and you will not be asked again.

If `subtree push` ever fails with a non-fast-forward error (which happens if the
`gh-pages` branch is edited on GitHub directly), overwrite it:

```bash
git push origin `git subtree split --prefix dist main`:gh-pages --force
```

GitHub's CDN caches for around ten minutes. If a change does not show, hard-reload
(`Ctrl+Shift+R`) before assuming the push failed.

---

## 2. Put it on Google Sites

Google Sites cannot host the file itself — it has no mechanism for serving
uploaded HTML. It can only *embed* a URL, which is why step 1 comes first.

### Embed it

1. Open <https://sites.google.com/view/abhishek23/> and click **Edit**.
2. Choose a **full-width section** for the embed. Sites gives a normal section
   about 640px of content width and a full-width section about 1030px. The
   layout is responsive either way, but 1030px is where it looks intended.
3. **Insert → Embed → Embed code** tab — *not* the **By URL** tab, which often
   renders a link-preview card instead of the live page. Paste:

```html
<iframe src="https://abhishm23.github.io/portfolio/"
        style="width:100%;height:1500px;border:0"
        title="Abhishek Mishra — portfolio"
        loading="lazy"></iframe>
```

4. **Next → Insert**, then drag the embed block to span the full section width
   and pull its bottom handle down until it stops clipping.
5. **Publish.** Embeds frequently show a grey placeholder in the editor and only
   render on the published site — check the published URL, not the editor
   preview, before concluding something is broken.

### Choosing the frame height

A Sites embed has a **fixed** height and never auto-resizes. This is the reason
the page is tabbed rather than one long scroll: instead of one 10,000px document,
each tab is close to a single frame. Measured heights of the rendered page:

| Tab | at 1030px (full-width) | at 640px (normal section) |
| --- | --- | --- |
| Profile | 1,090px | 1,334px |
| Capabilities | 1,438px | 2,006px |
| Experience | 1,307px | 1,840px |
| **Selected Work** | **3,398px** | **4,472px** |
| Credentials | 900px | 1,308px |
| Contact | 903px | 1,112px |

**Use `height:1500px`.** That fits five of the six tabs with no scrolling inside
the frame. Only Selected Work scrolls, which is fair — it is nine full project
cards, and anyone on that tab is deliberately reading depth.

The trade-off: Credentials and Contact are ~900px, so a 1500px frame leaves about
600px of empty page background under them. The background is near-black, so if
your Sites theme lets you give that section a dark background the seam
disappears. If the gap bothers you more than nested scrolling does, use
`height:1150px` instead — then Profile, Credentials and Contact fit exactly and
Capabilities and Experience scroll by a couple of hundred pixels.

On a phone Sites renders the embed at roughly 390px wide, where every tab is
taller than the frame. Nothing breaks; there is simply inner scrolling. The page
has no horizontal overflow at any width from 390px up.

The page `postMessage`s its height to the parent on load, resize, tab switch and
sub-tab change (`{ type: 'portfolio:height' }`). Google Sites ignores it — but if
you ever host the parent page yourself, listen for it and size the iframe to fit.

### Option B — embed the sections one at a time

If you would rather have each section as its own Sites block, interleaved with
your own text and images, add `?solo=1&tab=<key>` to the URL. That renders **one
panel alone** with the masthead, tab bar and footer stripped, so it drops into a
Sites section as a component rather than as a whole page.

```html
<iframe src="https://abhishm23.github.io/portfolio/?solo=1&amp;tab=experience"
        style="width:100%;height:1000px;border:0"
        title="Experience" loading="lazy"></iframe>
```

Six separate embeds, one URL each — no extra files to build or maintain. Measured
solo heights, with the value to type into Sites alongside:

| Section | URL suffix | Measured at 1030px | Use |
| --- | --- | --- | --- |
| Profile | `?solo=1&tab=profile` | 626px | 750px |
| Capabilities | `?solo=1&tab=capabilities` | 974px | 1100px |
| Experience | `?solo=1&tab=experience` | 843px | 1000px |
| Selected Work | `?solo=1&tab=work` | 2,976px | 3150px |
| Credentials | `?solo=1&tab=credentials` | 395px | 500px |
| Contact | `?solo=1&tab=contact` | 439px | 550px |

Solo heights are far below the tabbed ones because the masthead, tab bar and
footer are gone. The **Use** column adds ~125px of slack over the measurement:
text reflows a little at widths Sites picks that these numbers do not cover, and
a small gap is much better than a clipped card. In a 640px normal section the same
panels run taller — Capabilities 1,372px, Experience 1,206px, Selected Work
3,881px — so re-measure with `python tests/measure_heights.py` if you do not use
a full-width section.

Mixing the two is fine as well: one full tabbed embed on a landing section, plus
a solo Selected Work embed further down.

Related URL forms, if useful:

- `?tab=work` — full page with tabs, opening on Selected Work instead of Profile.
- `#credentials` — same effect via a hash. `?tab=` wins if both are present.
- An unknown key falls back to Profile rather than rendering nothing.

### Also add native Sites buttons

Whichever embed you use, put two Sites buttons (**Insert → Button**) directly
under it:

- `Open full portfolio →` → `https://abhishm23.github.io/portfolio/`
- `Download résumé (PDF)` → `https://abhishm23.github.io/portfolio/Abhishek_Mishra_Resume.pdf`

The second one matters more than it looks. Chrome blocks downloads started inside
a sandboxed iframe unless the sandbox permits them, and Sites does not. The
in-page download button carries `target="_blank"` so it degrades to opening the
PDF in a new tab rather than silently doing nothing — but a native Sites button
is the reliable path.

### What already accounts for the sandbox

No action needed on these; they are handled in the page:

- **No stored state.** `localStorage` and cookies can throw inside the Sites
  sandbox, so the page persists nothing. The active tab resets on reload by
  design.
- **No history entries.** The active tab is written to the URL with
  `replaceState`, not `pushState`. Pushing entries from inside an iframe would
  hijack the visitor's Back button on your Sites page.
- **External links open in a new tab.** LinkedIn and GitHub links carry
  `target="_blank" rel="noopener noreferrer"`. Without it they would load inside
  the small frame and replace the portfolio.
- **In-page anchors scroll the frame, not the host.** `initAnchors()` intercepts
  `href="#..."` clicks and calls `scrollIntoView` on the page's own document.
- **Fonts degrade gracefully.** The only external requests are two Google Fonts
  families. If they are blocked the page falls back to system fonts and nothing
  else changes.
- **A JS failure does not blank the frame.** Panels are hidden by script, not by
  markup, so in the worst case the embed shows one long scrolling page with all
  content present.
- **Motion respects the OS setting.** `prefers-reduced-motion: reduce` disables
  the aurora drift, starfield twinkle, 3D tilt, counters, panel transitions and
  reveal animations, and shows all content immediately.

---

## 3. Alternatives to GitHub Pages

Any of these works identically — the page is one file with no build step or
server requirement:

- **Netlify / Cloudflare Pages** — drag the `dist` folder onto the dashboard.
  HTTPS and a custom domain, no git required.
- **Google Drive** — does *not* work. Drive stopped serving HTML as web pages in
  2016.
- **Google Sites' own file cabinet** — does not work either; there is no way to
  serve raw HTML from Sites.
