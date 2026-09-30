import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    os.makedirs('docs/screenshots', exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("Navigating to dashboard...")
        await page.goto('http://localhost:5173')
        await page.wait_for_timeout(3000)
        
        print("Taking full overview screenshot...")
        await page.screenshot(path='docs/screenshots/dashboard_overview.png')
        
        print("Clicking a hazard cluster...")
        # click a hazard marker (bg-[#C76A1E])
        amber_marker = page.locator('div.bg-\\[\\#C76A1E\\]').first
        if await amber_marker.count() > 0:
            await amber_marker.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path='docs/screenshots/hazard_cluster.png')
            await page.mouse.click(0, 0)
            await page.wait_for_timeout(500)
        
        print("Clicking demo trajectory button...")
        demo_btn = page.locator('button:has-text("Show Demo:")')
        if await demo_btn.count() > 0:
            await demo_btn.click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path='docs/screenshots/demo_trajectory.png')
            
        await browser.close()
        print("Screenshots saved to docs/screenshots/")

if __name__ == '__main__':
    asyncio.run(main())
