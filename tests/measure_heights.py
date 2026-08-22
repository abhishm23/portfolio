"""Height table (and optional screenshots) at the widths a Sites embed can take.

    python tests/measure_heights.py                    # just the table
    python tests/measure_heights.py 1030:work 390:profile   # + screenshots

Google Sites gives an embed a FIXED height that never auto-resizes, so the
number you type into the Sites editor has to come from a measurement at the
width Sites actually renders — roughly 640px in a normal section and 1030px in
a full-width one. The MAX column is the height at which no panel ever needs
in-frame scrolling; DEPLOY.md explains why a smaller value is usually better.
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "file:///" + os.path.join(ROOT, "dist", "index.html").replace(os.sep, "/").lstrip("/")
TABS = ["profile", "capabilities", "experience", "work", "credentials", "contact"]

WIDTHS = [390, 640, 768, 1030, 1440]


async def main():
    shots = sys.argv[1:]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        print("  full-document height per tab (px)")
        print("  width  " + "".join(f"{t[:6]:>9}" for t in TABS) + f"{'MAX':>9}")
        for w in WIDTHS:
            ctx = await browser.new_context(viewport={"width": w, "height": 900})
            page = await ctx.new_page()
            await page.goto(BASE, wait_until="load")
            await page.wait_for_timeout(500)
            row = []
            for key in TABS:
                await page.click(f".tab[data-tab='{key}']")
                await page.wait_for_timeout(420)
                row.append(await page.evaluate("document.documentElement.scrollHeight"))
            sw = await page.evaluate("document.documentElement.scrollWidth")
            flag = "  OVERFLOW" if sw > w + 1 else ""
            print(f"  {w:>5}  " + "".join(f"{v:>9}" for v in row) + f"{max(row):>9}{flag}")
            await ctx.close()

        # Screenshots of whichever tabs were named on the command line. Written
        # to _shot_<width>_<tab>.png, which .gitignore excludes.
        for spec in shots:
            width, _, key = spec.partition(":")
            key = key or "profile"
            w = int(width)
            ctx = await browser.new_context(viewport={"width": w, "height": 900},
                                            device_scale_factor=2)
            page = await ctx.new_page()
            await page.goto(BASE, wait_until="networkidle")
            await page.evaluate("document.fonts && document.fonts.ready")
            await page.click(f".tab[data-tab='{key}']")
            await page.wait_for_timeout(1800)
            out = os.path.join(ROOT, f"_shot_{w}_{key}.png")
            await page.screenshot(path=out, full_page=True)
            h = await page.evaluate("document.documentElement.scrollHeight")
            print(f"  -> {os.path.basename(out)}  ({w}x{h} css px)")
            await ctx.close()

        await browser.close()


asyncio.run(main())
