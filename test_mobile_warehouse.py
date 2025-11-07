#!/usr/bin/env python3
"""
Mobile Viewport Testing for Warehouse-Mode Pages
Captures screenshots at 375px width and measures button sizes
"""
import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    base_url = "http://127.0.0.1:5000"
    
    print(f"🔍 Testing warehouse-mode pages at 375px width")
    print(f"📱 Viewport: 375px × 667px (iPhone SE)")
    print(f"🌐 Base URL: {base_url}\n")
    
    async with async_playwright() as p:
        # Launch browser using system Chromium
        browser = await p.chromium.launch(
            executable_path="/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium"
        )
        
        # Create mobile context
        context = await browser.new_context(
            viewport={'width': 375, 'height': 667},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        
        page = await context.new_page()
        
        # Create screenshots directory
        os.makedirs("/tmp/mobile_screenshots", exist_ok=True)
        
        try:
            # Test 1: Login page (public)
            print("1️⃣  Testing /login")
            await page.goto(f"{base_url}/login", wait_until="networkidle", timeout=10000)
            await page.screenshot(path="/tmp/mobile_screenshots/01_login_375px.png", full_page=True)
            
            # Measure buttons on login page
            buttons = await page.query_selector_all("button, .btn, .wh-btn")
            for i, btn in enumerate(buttons[:3]):
                box = await btn.bounding_box()
                if box:
                    print(f"   Button {i+1}: {box['height']:.1f}px height × {box['width']:.1f}px width")
            
            # Login as admin
            print("\n2️⃣  Logging in as admin...")
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', admin_password)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle")
            print("   ✅ Logged in successfully")
            
            # Test 2: Create Bill page
            print("\n3️⃣  Testing /bills/create")
            await page.goto(f"{base_url}/bills/create", wait_until="networkidle", timeout=10000)
            await page.screenshot(path="/tmp/mobile_screenshots/02_create_bill_375px.png", full_page=True)
            
            # Measure input and button sizes
            scanner_input = await page.query_selector('input[type="text"]')
            if scanner_input:
                box = await scanner_input.bounding_box()
                print(f"   Scanner input: {box['height']:.1f}px height × {box['width']:.1f}px width")
            
            submit_button = await page.query_selector('button[type="submit"]')
            if submit_button:
                box = await submit_button.bounding_box()
                print(f"   Submit button: {box['height']:.1f}px height × {box['width']:.1f}px width")
            
            # Test 3: Scan Bill Parent page
            print("\n4️⃣  Testing /bills/scan_parent")
            await page.goto(f"{base_url}/bills/scan_parent", wait_until="networkidle", timeout=10000)
            await page.screenshot(path="/tmp/mobile_screenshots/03_scan_bill_parent_375px.png", full_page=True)
            
            buttons = await page.query_selector_all(".wh-btn")
            for i, btn in enumerate(buttons[:3]):
                box = await btn.bounding_box()
                if box:
                    print(f"   Button {i+1}: {box['height']:.1f}px height × {box['width']:.1f}px width")
            
            # Test 4: Scan Child page
            print("\n5️⃣  Testing /scan/child")
            await page.goto(f"{base_url}/scan/child", wait_until="networkidle", timeout=10000)
            await page.screenshot(path="/tmp/mobile_screenshots/04_scan_child_375px.png", full_page=True)
            
            # Measure counter display
            counter = await page.query_selector('#count')
            if counter:
                style = await counter.evaluate('el => window.getComputedStyle(el).fontSize')
                print(f"   Counter font size: {style}")
            
            buttons = await page.query_selector_all(".wh-btn")
            for i, btn in enumerate(buttons[:3]):
                box = await btn.bounding_box()
                if box:
                    print(f"   Button {i+1}: {box['height']:.1f}px height × {box['width']:.1f}px width")
            
            # Test 5: Bill Management page
            print("\n6️⃣  Testing /bills")
            await page.goto(f"{base_url}/bills", wait_until="networkidle", timeout=10000)
            await page.screenshot(path="/tmp/mobile_screenshots/05_bill_management_375px.png", full_page=True)
            
            search_input = await page.query_selector('input[type="search"], input[name="search_bill_id"]')
            if search_input:
                box = await search_input.bounding_box()
                print(f"   Search input: {box['height']:.1f}px height × {box['width']:.1f}px width")
            
            # Measure specific wh-btn buttons with their text
            wh_btns = await page.query_selector_all(".wh-btn")
            print(f"   Found {len(wh_btns)} .wh-btn buttons")
            for i, btn in enumerate(wh_btns[:5]):
                box = await btn.bounding_box()
                text = (await btn.inner_text()).strip()[:30]  # First 30 chars
                if box:
                    print(f"   .wh-btn #{i+1} '{text}': {box['height']:.1f}px height")
            
            # Also check if any non-wh-btn buttons exist
            all_btns = await page.query_selector_all("button, .btn")
            non_wh = [b for b in all_btns if not await b.get_attribute("class") or "wh-btn" not in await b.get_attribute("class")]
            if non_wh:
                print(f"   ⚠️  Found {len(non_wh)} non-warehouse buttons!")
            
            print("\n✅ All screenshots captured successfully!")
            print(f"📂 Screenshots saved to: /tmp/mobile_screenshots/")
            print("\n📋 Summary:")
            print("   - All pages tested at 375px width")
            print("   - Button heights measured (target: 60-80px)")
            print("   - Input heights measured (target: 60px+)")
            print("   - Font sizes checked (target: 18-24px+)")
            
        except Exception as e:
            print(f"\n❌ Error during testing: {e}")
            await page.screenshot(path="/tmp/mobile_screenshots/error.png")
            raise
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
