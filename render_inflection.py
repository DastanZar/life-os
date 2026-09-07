import asyncio
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        try:
            b = await p.chromium.launch()
        except Exception:
            b = await p.chromium.launch(executable_path="/usr/bin/chromium-browser",
                                        args=["--no-sandbox","--disable-gpu"])
        pg = await b.new_page(viewport={"width":1040,"height":900}, device_scale_factor=2)
        await pg.goto("file:///home/ubuntu/life-os/inflection_solutions_flowchart.html")
        await pg.wait_for_timeout(600)
        for i, name in enumerate(["master_map","b1_backprop","c1_styleencoder"]):
            h2s = await pg.query_selector_all("h2")
            svg = await h2s[i].query_selector("xpath=following-sibling::svg[1]")
            await svg.screenshot(path=f"/home/ubuntu/life-os/inflection_{name}.png")
            print("shot", name)
        await b.close()
asyncio.run(main())
