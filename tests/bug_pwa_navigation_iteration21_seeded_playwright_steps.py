"""
Seeded focused Playwright steps executed for iteration 21.

Prerequisite: run bug_pwa_navigation_iteration21_seed_toggle.py setup, then run
these steps, then run ...seed_toggle.py restore. This exposes Luca's
MioTerapeutaCard with a temporary Maria Rossi slot so both home actions can be
clicked through the real UI.
"""

BASE_URL = "https://portugues-writer-2.preview.emergentagent.com"
THERAPIST_ID = "69e5c83ca585e313092bd593"


async def run(page):
    console_messages = []
    page_errors = []
    page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    async def current_path():
        return await page.evaluate("window.location.pathname + window.location.search")

    async def reject_cookies_if_present():
        if await page.locator('[data-testid="cookie-reject-all-btn"]').count() > 0:
            await page.locator('[data-testid="cookie-reject-all-btn"]').click(force=True)
            await page.wait_for_timeout(300)

    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(f"{BASE_URL}/login?app=1", wait_until="domcontentloaded")
    await reject_cookies_if_present()
    await page.locator('[data-testid="login-email"]').fill("demo.paziente@funzionabene.it")
    await page.locator('[data-testid="login-password"]').fill("paziente2026")
    await page.locator('[data-testid="login-submit"]').click()
    await page.wait_for_url("**/paziente", timeout=15000)

    await page.goto(f"{BASE_URL}/paziente?app=1", wait_until="networkidle")
    await page.locator('[data-testid="home-mio-terapeuta"]').wait_for(timeout=15000)
    await page.locator('[data-testid="home-cerca-altro"]').click(force=True)
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)
    assert await current_path() == "/questionario"

    await page.goto(f"{BASE_URL}/terapeuti", wait_until="networkidle")
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)
    assert await current_path() == "/questionario"

    await page.goto(f"{BASE_URL}/paziente?app=1", wait_until="networkidle")
    await page.locator('[data-testid="home-mio-terapeuta"]').wait_for(timeout=15000)
    await page.locator('[data-testid="home-prenota-mio-terapeuta"]').click(force=True)
    await page.locator('[data-testid="therapist-public"]').wait_for(timeout=15000)
    await page.locator('[data-testid="booking-sheet"]').wait_for(timeout=15000)

    await page.goto(f"{BASE_URL}/terapeuti/{THERAPIST_ID}?prenota=1", wait_until="networkidle")
    await page.locator('[data-testid="therapist-public"]').wait_for(timeout=15000)
    await page.locator('[data-testid="booking-sheet"]').wait_for(timeout=15000)

    await page.goto(f"{BASE_URL}/questionario", wait_until="networkidle")
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)

    for marketing_path in ["/blog", "/chi-siamo"]:
        await page.goto(f"{BASE_URL}{marketing_path}", wait_until="networkidle")
        await page.wait_for_url("**/paziente", timeout=15000)
        await page.locator('[data-testid="paziente-home"]').wait_for(timeout=15000)

    await page.evaluate("sessionStorage.removeItem('__preview-app-mode')")
    await page.goto(f"{BASE_URL}/terapeuti/{THERAPIST_ID}", wait_until="networkidle")
    await page.locator('[data-testid="therapist-public"]').wait_for(timeout=15000)
    await page.goto(f"{BASE_URL}/questionario", wait_until="networkidle")
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)

    assert not [m for m in console_messages + page_errors if "groupByDate" in m]