import asyncio
from playwright.async_api import async_playwright
import os

async def test_mobile_pages():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await p.browser.new_context(
            viewport={'width': 375, 'height': 667},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        
        base_url = "http://127.0.0.1:5000"
        pages_to_test = [
            ("/login", "login_page"),
            ("/", "home_page"),
        ]
        
        os.makedirs("/tmp/mobile_screenshots", exist_ok=True)
        
        for path, name in pages_to_test:
            try:
                await page.goto(f"{base_url}{path}", wait_until="networkidle", timeout=10000)
                await page.screenshot(path=f"/tmp/mobile_screenshots/{name}_375px.png", full_page=True)
                print(f"✅ Captured: {name}")
                
                # Get button sizes if any
                buttons = await page.query_selector_all("button, .wh-btn, .btn")
                for i, btn in enumerate(buttons[:3]):  # First 3 buttons only
                    box = await btn.bounding_box()
                    if box:
                        print(f"  Button {i+1}: {box['height']:.1f}px height, {box['width']:.1f}px width")
            except Exception as e:
                print(f"❌ Failed {name}: {e}")
        
        await browser.close()
        print("\n📸 Screenshots saved to /tmp/mobile_screenshots/")
        print("✅ Mobile viewport testing complete!")

asyncio.run(test_mobile_pages())
