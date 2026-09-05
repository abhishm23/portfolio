"""Behavioural check of the tabbed portfolio page. Run after every build.

    python tests/verify_portfolio.py

Verifies that exactly one panel is ever in the layout, that every tab resolves
its own content, that reveal recovers on panel switch (elements observed while
display:none report no intersection forever), that the solo-embed mode strips
chrome, and that YAML coverage survived any restructure. Exits non-zero on the
first failing assertion so it can gate a commit.
"""
import asyncio
import os
import re
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "file:///" + os.path.join(ROOT, "dist", "index.html").replace(os.sep, "/").lstrip("/")

TABS = ["profile", "capabilities", "experience", "work", "credentials", "contact"]

# What must be present and non-empty in each panel, so a silently emptied
# panel cannot pass.
EXPECT = {
    "profile": (".lede", 2),
    "capabilities": (".skill-card", 5),
    "experience": (".card .bullet-list li", 7),
    "work": (".pillar:not(.is-hidden) .project-card", 3),
    "credentials": (".cred-list", 3),
    "contact": (".closer .link-pill", 5),
}

ok, bad = [], []


def check(label, condition, detail=""):
    (ok if condition else bad).append(f"{label}{(' — ' + detail) if detail else ''}")


async def visible_panels(page):
    return await page.evaluate(
        "Array.from(document.querySelectorAll('.panel'))"
        ".filter(p => !p.hidden).map(p => p.dataset.panel)"
    )


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append("console." + m.type + ": " + m.text)
                if m.type == "error" else None)

        await page.goto(BASE, wait_until="networkidle")
        await page.evaluate("document.fonts && document.fonts.ready")
        await page.wait_for_timeout(800)

        # --- one panel at a time, defaulting to profile -----------------------
        vis = await visible_panels(page)
        check("exactly one panel visible on load", len(vis) == 1, str(vis))
        check("default tab is Profile", vis == ["profile"], str(vis))

        total_panels = await page.evaluate("document.querySelectorAll('.panel').length")
        check("all six panels present in the DOM", total_panels == 6, str(total_panels))

        # --- every tab resolves its own content ------------------------------
        for key in TABS:
            await page.click(f".tab[data-tab='{key}']")
            await page.wait_for_timeout(700)

            vis = await visible_panels(page)
            check(f"tab '{key}' shows only its panel", vis == [key], str(vis))

            sel, want = EXPECT[key]
            got = await page.evaluate(
                f"document.querySelectorAll('#panel-{key} {sel}').length"
            )
            check(f"panel '{key}' renders its content", got == want, f"{got} of {want} ({sel})")

            aria = await page.get_attribute(f".tab[data-tab='{key}']", "aria-selected")
            check(f"tab '{key}' reports aria-selected", aria == "true", str(aria))

            # Reveal must recover for a panel that was display:none when the
            # observer last evaluated it. Zero-size elements are excluded for
            # the same reason the sweep skips them: inside the Work panel two
            # of three pillars are display:none, so their cards measure 0x0 at
            # the origin and would otherwise read as "in view".
            hidden = await page.evaluate(
                f"document.querySelectorAll('#panel-{key} .reveal:not(.is-in)').length"
            )
            in_view = await page.evaluate(
                f"""Array.from(document.querySelectorAll('#panel-{key} .reveal:not(.is-in)'))
                    .filter(e => {{
                        const r = e.getBoundingClientRect();
                        return (r.width || r.height) && r.top < window.innerHeight;
                    }}).length"""
            )
            check(f"panel '{key}' reveals what is in view", in_view == 0,
                  f"{in_view} in-view still hidden ({hidden} total pending)")

        # --- work sub-tabs ---------------------------------------------------
        await page.click(".tab[data-tab='work']")
        await page.wait_for_timeout(400)
        three = await page.evaluate(
            "document.querySelectorAll('.pillar:not(.is-hidden) .project-card').length")
        check("Work opens at one discipline", three == 3, f"{three} cards")

        await page.click(".filter[data-filter='all']")
        await page.wait_for_timeout(500)
        nine = await page.evaluate(
            "document.querySelectorAll('.pillar:not(.is-hidden) .project-card').length")
        check("'All 9' restores every card", nine == 9, f"{nine} cards")

        # Worst case for the tallest panel: instant jump to the bottom with all
        # nine cards showing. Nothing may be left invisible.
        await page.evaluate(
            "document.documentElement.style.scrollBehavior='auto';"
            "window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1400)
        left = await page.evaluate(
            "document.querySelectorAll('#panel-work .reveal:not(.is-in)').length")
        check("every Work reveal resolves after a full scroll", left == 0, f"{left} left hidden")
        await page.evaluate("window.scrollTo(0, 0)")

        # --- counters land on the authored value ------------------------------
        await page.click(".tab[data-tab='profile']")
        await page.wait_for_timeout(1800)
        stats = await page.evaluate(
            "Array.from(document.querySelectorAll('.stat-value')).map(e => e.textContent.trim())")
        check("hero stats show authored values", stats == ["6+", "9", "20M+", "32"], str(stats))

        await page.click(".tab[data-tab='work']")
        await page.click(".filter[data-filter='all']")
        await page.wait_for_timeout(1800)
        stuck = await page.evaluate(
            "Array.from(document.querySelectorAll('.metric-value'))"
            ".map(e => e.textContent.trim())"
            ".filter(t => /\\d/.test(t) && !/^[^\\d]*\\d[\\d.,+%A-Za-z /-]*$/.test(t))")
        check("no metric left mid-animation", len(stuck) == 0, str(stuck))

        ranges = await page.evaluate(
            "Array.from(document.querySelectorAll('.metric-value'))"
            ".map(e => e.textContent.trim()).filter(t => t.indexOf('-') > 0)")
        check("range metrics preserved verbatim",
              "1-2%" in ranges and "40-50%" in ranges, str(ranges))

        # --- total YAML coverage across all panels ---------------------------
        coverage = await page.evaluate("""({
            cards:   document.querySelectorAll('.project-card').length,
            skills:  document.querySelectorAll('.skill-card').length,
            bullets: document.querySelectorAll('.bullet-list li').length,
            metrics: document.querySelectorAll('.metric').length,
            flags:   document.querySelectorAll('.flag-tag').length
        })""")
        check("full YAML coverage retained",
              coverage == {"cards": 9, "skills": 5, "bullets": 7, "metrics": 18, "flags": 3},
              str(coverage))

        # --- data-goto cross-panel jump --------------------------------------
        await page.click(".tab[data-tab='profile']")
        await page.wait_for_timeout(300)
        await page.click(".ghost-cta[data-goto='work']")
        await page.wait_for_timeout(400)
        vis = await visible_panels(page)
        check("in-panel CTA switches tabs", vis == ["work"], str(vis))

        # --- keyboard ---------------------------------------------------------
        await page.click(".tab[data-tab='profile']")
        await page.wait_for_timeout(200)
        await page.focus(".tab[data-tab='profile']")
        await page.keyboard.press("ArrowRight")
        await page.wait_for_timeout(400)
        vis = await visible_panels(page)
        check("ArrowRight moves to the next tab", vis == ["capabilities"], str(vis))
        await page.keyboard.press("End")
        await page.wait_for_timeout(400)
        vis = await visible_panels(page)
        check("End jumps to the last tab", vis == ["contact"], str(vis))

        # --- deep link --------------------------------------------------------
        await page.goto(BASE + "?tab=experience", wait_until="load")
        await page.wait_for_timeout(600)
        vis = await visible_panels(page)
        check("?tab= preselects a panel", vis == ["experience"], str(vis))

        await page.goto(BASE + "#credentials", wait_until="load")
        await page.wait_for_timeout(600)
        vis = await visible_panels(page)
        check("#hash preselects a panel", vis == ["credentials"], str(vis))

        await page.goto(BASE + "?tab=nonsense", wait_until="load")
        await page.wait_for_timeout(600)
        vis = await visible_panels(page)
        check("unknown ?tab= falls back to the default", vis == ["profile"], str(vis))

        # --- solo embed mode --------------------------------------------------
        await page.goto(BASE + "?solo=1&tab=experience", wait_until="load")
        await page.wait_for_timeout(700)
        chrome = await page.evaluate("""({
            solo: document.body.classList.contains('is-solo'),
            mast: getComputedStyle(document.querySelector('.masthead')).display,
            tabs: getComputedStyle(document.querySelector('.tabbar')).display
        })""")
        check("?solo=1 strips the chrome",
              chrome["solo"] and chrome["mast"] == "none" and chrome["tabs"] == "none",
              str(chrome))
        vis = await visible_panels(page)
        check("?solo=1 shows only the requested panel", vis == ["experience"], str(vis))
        bullets = await page.evaluate("document.querySelectorAll('.bullet-list li').length")
        check("solo panel still renders content", bullets == 7, f"{bullets} bullets")

        # --- panel heights ----------------------------------------------------
        await page.goto(BASE, wait_until="load")
        await page.wait_for_timeout(500)
        heights = {}
        for key in TABS:
            await page.click(f".tab[data-tab='{key}']")
            await page.wait_for_timeout(450)
            heights[key] = await page.evaluate("document.documentElement.scrollHeight")
        check("no uncaught page or console errors", not errors, str(errors[:4]))

        # --- deliverable & GitHub repo URLs verification ---------------------
        top5_repos = [
            "https://github.com/abhishm23/LLM-Forge",
            "https://github.com/abhishm23/Research-Arena",
            "https://github.com/abhishm23/BHOLA-Coding-Agent",
            "https://github.com/abhishm23/AutonomousJobApplicant",
            "https://github.com/abhishm23/AetherHarvest",
        ]
        profile_path = os.path.join(ROOT, "dist", "portfolio_profile.html")
        check("dist/portfolio_profile.html exists", os.path.exists(profile_path))
        if os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as pf:
                profile_html = pf.read()
            for repo_url in top5_repos:
                check(f"portfolio_profile.html contains {repo_url.split('/')[-1]} repo link",
                      repo_url in profile_html, repo_url)

        pdf_path = os.path.join(ROOT, "dist", "Abhishek_Mishra_Resume.pdf")
        check("dist/Abhishek_Mishra_Resume.pdf exists", os.path.exists(pdf_path))
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as fh:
                raw_pdf = fh.read()
            counts = [int(n) for n in re.findall(rb"/Count\s+(\d+)", raw_pdf)]
            pdf_pages = max(counts) if counts else 0
            check("Abhishek_Mishra_Resume.pdf has exactly 1 page", pdf_pages == 1, f"{pdf_pages} pages")

        await browser.close()

    for line in ok:
        print(f"  PASS  {line}")
    for line in bad:
        print(f"  FAIL  {line}")
    print(f"\n{len(ok)} passed, {len(bad)} failed")
    print("\n  full-document height per tab at 1440px:")
    for key, h in heights.items():
        print(f"    {key:<14} {h:>6}px")
    print(f"    {'TALLEST':<14} {max(heights.values()):>6}px")
    return 1 if bad else 0


sys.exit(asyncio.run(main()))
