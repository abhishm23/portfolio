# Deploying the portfolio page

`dist/index.html` is a single self-contained file. Anything that can serve one static HTML file over HTTPS can host it. Below is the GitHub Pages route, then how to surface it on Google Sites.

---

## 1. Publish `dist/` to GitHub Pages

Create a repo (public — Pages needs public unless you have a paid plan), then push the sources and publish only `dist/` to a `gh-pages` branch:

```bash
git init && git add -A && git commit -m "Résumé and portfolio pipeline"
```

```bash
git remote add origin https://github.com/abhishek23/portfolio.git && git push -u origin main
```

```bash
git subtree push --prefix dist origin gh-pages
```

Then in the repo: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `gh-pages` / `(root)` → Save.**

`build_resume.py` already writes `dist/.nojekyll`, which tells Pages to serve the directory verbatim instead of running it through Jekyll.

After a minute or two you have:

```
https://abhishek23.github.io/portfolio/
https://abhishek23.github.io/portfolio/Abhishek_Mishra_Resume.pdf
```

**To publish updates** — rebuild, commit, and push the subtree again:

```bash
python build_resume.py && git add -A && git commit -m "Update content" && git push && git subtree push --prefix dist origin gh-pages
```

GitHub's CDN caches for around ten minutes. If you do not see a change, hard-reload (`Ctrl+Shift+R`) before assuming the push failed.

---

## 2. Put it on Google Sites

Google Sites cannot host the file itself — it has no file-upload-and-serve mechanism for HTML. It can only *embed* a URL, which is why step 1 comes first.

### Embed it

1. Open your site at `sites.google.com/view/abhishek23` and click **Edit**.
2. Choose a **full-width section** for the embed. Sites gives a normal section about 640px of content width and a full-width section about 1030px. The layout is responsive either way, but 1030px is where it looks intended.
3. **Insert → Embed → Embed code** tab (not the *By URL* tab — that one often renders a link preview card instead of the live page). Paste:

```html
<iframe src="https://abhishek23.github.io/portfolio/"
        style="width:100%;height:1100px;border:0"
        title="Abhishek Mishra — portfolio"
        loading="lazy"></iframe>
```

4. Click **Next → Insert**, then drag the embed block to span the full section width and pull its bottom handle down as far as you want.
5. **Publish.** Embeds frequently show a grey placeholder in the editor and only render on the published site — check the published URL, not the editor preview, before concluding something is broken.

### The one limitation to plan around

**Google Sites embeds have a fixed height and do not auto-resize.** Whatever height you set, the page scrolls *inside* the frame. The content is genuinely long — measured heights of the rendered page:

| Frame width | Content height |
| --- | --- |
| 1440px | 10,310px |
| 1030px (Sites full-width) | 10,960px |
| 950px | 11,877px |
| 768px (tablet) | 13,352px |
| 640px (Sites normal section) | 14,419px |
| 390px (phone) | 18,995px |

So an 1100px-tall frame shows roughly a tenth of the page at a time. That is workable but it means nested scrolling: the wheel scrolls the frame until it bottoms out, then the Sites page starts moving.

The page tries to `postMessage` its height to the parent on load, resize, and filter change (`{ type: 'portfolio:height' }`). Google Sites ignores it, but if you ever host the parent page yourself you can listen for it and resize the iframe to fit.

### Recommended: embed *and* link out

Given 10,000+ pixels of content, the best experience is both. Directly under the embed, add a Sites **Button** (Insert → Button):

- Label: `Open full portfolio →`
- Link: `https://abhishek23.github.io/portfolio/`

And a second button for the résumé:

- Label: `Download résumé (PDF)`
- Link: `https://abhishek23.github.io/portfolio/Abhishek_Mishra_Resume.pdf`

That second button matters more than it looks. Chrome blocks downloads initiated inside a sandboxed iframe unless the sandbox allows them, and Sites does not. The in-page download link carries `target="_blank"` so it falls back to opening the PDF in a new tab rather than silently doing nothing — but a native Sites button is the reliable path.

### What already accounts for the sandbox

No action needed on these; they are handled in the page:

- **No stored state.** `localStorage` and cookies can throw inside the Sites sandbox, so the page persists nothing. The project filter resets on reload by design.
- **External links open in a new tab.** LinkedIn and GitHub links carry `target="_blank" rel="noopener noreferrer"`. Without it they would load inside the small frame and replace the portfolio.
- **In-page anchors scroll the frame, not the host.** `initAnchors()` intercepts `href="#..."` clicks and calls `scrollIntoView` on the page's own document.
- **Fonts degrade gracefully.** The only external requests are two Google Fonts families. If they are blocked, the page falls back to system fonts and nothing else changes.
- **Motion respects the OS setting.** `prefers-reduced-motion: reduce` disables the aurora drift, starfield twinkle, 3D tilt, counters, and reveal transitions, and shows all content immediately.

---

## 3. Alternatives to GitHub Pages

Any of these works identically — the page is one file with no build step or server requirement:

- **Netlify / Cloudflare Pages** — drag the `dist` folder onto the dashboard. Gives HTTPS and a custom domain, no git required.
- **Google Drive** — does *not* work. Drive stopped serving HTML as web pages in 2016.
- **Google Sites' own file cabinet** — does not work either; there is no way to serve raw HTML from Sites.
