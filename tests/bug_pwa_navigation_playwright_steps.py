"""
Focused Playwright steps for the Luca standalone-PWA therapist navigation bug.

This file mirrors the script executed through the browser automation tool.
It intentionally covers only the reported flow and direct regressions.
"""

BASE_URL = "https://portugues-writer-2.preview.emergentagent.com"
THERAPIST_ID = "69e5c83ca585e313092bd593"
APPOINTMENT_ID = "6a744d716e6732478951de81"


async def run(page):
    async def path():
        return await page.evaluate("window.location.pathname + window.location.search")

    async def visible(testid):
        return await page.locator(f'[data-testid="{testid}"]').count() > 0 and await page.locator(f'[data-testid="{testid}"]').first.is_visible()

    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
    if await page.locator('[data-testid="cookie-reject-all-btn"]').count() > 0:
        await page.locator('[data-testid="cookie-reject-all-btn"]').click(force=True)
    await page.locator('[data-testid="login-email"]').fill("demo.paziente@funzionabene.it")
    await page.locator('[data-testid="login-password"]').fill("paziente2026")
    await page.locator('[data-testid="login-submit"]').click()
    await page.wait_for_url("**/paziente", timeout=15000)

    await page.goto(f"{BASE_URL}/paziente?app=1", wait_until="networkidle")
    await page.locator('[data-testid="paziente-home"]').wait_for(timeout=15000)

    # Core allowed standalone routes
    await page.goto(f"{BASE_URL}/terapeuti/{THERAPIST_ID}?prenota=1", wait_until="networkidle")
    await page.locator('[data-testid="therapist-public"]').wait_for(timeout=15000)

    await page.goto(f"{BASE_URL}/terapeuti", wait_until="networkidle")
    # Expected product outcome: therapist listing/options. Actual failure if 404 renders.

    await page.goto(f"{BASE_URL}/questionario", wait_until="networkidle")
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)

    # Standalone marketing redirect regression
    await page.goto(f"{BASE_URL}/blog", wait_until="networkidle")
    await page.locator('[data-testid="paziente-home"]').wait_for(timeout=15000)

    # Standalone video route regression
    await page.goto(f"{BASE_URL}/seduta/{APPOINTMENT_ID}", wait_until="domcontentloaded")
    await page.locator('[data-testid="video-call-page"]').wait_for(timeout=15000)

    # Normal browser mode: clear the preview standalone flag and confirm /blog works.
    await page.evaluate("sessionStorage.removeItem('__preview-app-mode')")
    await page.goto(f"{BASE_URL}/blog", wait_until="networkidle")
    await page.locator('[data-testid="blog-page"]').wait_for(timeout=15000)