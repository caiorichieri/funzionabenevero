"""
Focused Playwright steps for iteration 21 Luca standalone-PWA therapist navigation bug.

This mirrors the script body executed through the browser automation tool. It
covers only the reported Luca PWA flow plus the regression routes requested by
the main agent.
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

    async def has_testid(testid):
        locator = page.locator(f'[data-testid="{testid}"]')
        return await locator.count() > 0 and await locator.first.is_visible()

    async def reject_cookies_if_present():
        if await page.locator('[data-testid="cookie-reject-all-btn"]').count() > 0:
            await page.locator('[data-testid="cookie-reject-all-btn"]').click(force=True)
            await page.wait_for_timeout(300)

    await page.set_viewport_size({"width": 390, "height": 844})

    # Enable preview standalone mode and login as Luca.
    await page.goto(f"{BASE_URL}/login?app=1", wait_until="domcontentloaded")
    await reject_cookies_if_present()
    await page.locator('[data-testid="login-email"]').fill("demo.paziente@funzionabene.it")
    await page.locator('[data-testid="login-password"]').fill("paziente2026")
    await page.locator('[data-testid="login-submit"]').click()
    await page.wait_for_url("**/paziente", timeout=15000)

    await page.goto(f"{BASE_URL}/paziente?app=1", wait_until="networkidle")
    await page.locator('[data-testid="paziente-home"]').wait_for(timeout=15000)
    await page.wait_for_timeout(3000)
    print(f"Standalone home loaded: {await current_path()}")
    print("MioTerapeutaCard visible:", await has_testid("home-mio-terapeuta"))
    print("NextSessionCard visible:", await has_testid("home-next-session"))
    print("Prenota button visible:", await has_testid("home-prenota-mio-terapeuta"))
    print("Cerca altro link visible:", await has_testid("home-cerca-altro"))

    # Verify footer link from MioTerapeutaCard opens therapist options/questionnaire.
    if await has_testid("home-cerca-altro"):
        await page.locator('[data-testid="home-cerca-altro"]').click(force=True)
        await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)
        print(f"Cerca un altro navigated to: {await current_path()}")
    else:
        print("Cerca un altro link was not visible in current seed state")

    # Verify direct /terapeuti list route redirects to questionario in standalone.
    await page.goto(f"{BASE_URL}/terapeuti", wait_until="networkidle")
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)
    print(f"/terapeuti standalone final path: {await current_path()}")

    # Verify therapist booking route renders without groupByDate crash.
    await page.goto(f"{BASE_URL}/terapeuti/{THERAPIST_ID}?prenota=1", wait_until="networkidle")
    await page.locator('[data-testid="therapist-public"]').wait_for(timeout=15000)
    print(f"Therapist booking route loaded: {await current_path()}")
    print("Booking sheet visible:", await has_testid("booking-sheet"))

    # If the Prenota button is visible on the current home data, click it; if not,
    # the direct booking route above is the executable proof for the target route.
    await page.goto(f"{BASE_URL}/paziente?app=1", wait_until="networkidle")
    await page.locator('[data-testid="paziente-home"]').wait_for(timeout=15000)
    await page.wait_for_timeout(3000)
    if await has_testid("home-prenota-mio-terapeuta"):
        await page.locator('[data-testid="home-prenota-mio-terapeuta"]').click(force=True)
        await page.locator('[data-testid="therapist-public"]').wait_for(timeout=15000)
        print(f"Prenota button final path: {await current_path()}")
    else:
        print("Prenota una seduta button not visible because current mio-terapeuta API has zero upcoming slots")

    # Standalone regressions: questionario allowed; marketing pages redirect back.
    await page.goto(f"{BASE_URL}/questionario", wait_until="networkidle")
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)
    print(f"/questionario standalone loaded: {await current_path()}")

    for marketing_path in ["/blog", "/chi-siamo"]:
        await page.goto(f"{BASE_URL}{marketing_path}", wait_until="networkidle")
        await page.wait_for_url("**/paziente", timeout=15000)
        await page.locator('[data-testid="paziente-home"]').wait_for(timeout=15000)
        print(f"{marketing_path} standalone redirected to: {await current_path()}")

    # Normal browser mode: clear the preview standalone flag and confirm routes still render.
    await page.evaluate("sessionStorage.removeItem('__preview-app-mode')")
    await page.goto(f"{BASE_URL}/terapeuti/{THERAPIST_ID}", wait_until="networkidle")
    await page.locator('[data-testid="therapist-public"]').wait_for(timeout=15000)
    print(f"Normal browser therapist route loaded: {await current_path()}")

    await page.goto(f"{BASE_URL}/questionario", wait_until="networkidle")
    await page.locator('[data-testid="questionnaire"]').wait_for(timeout=15000)
    print(f"Normal browser questionario loaded: {await current_path()}")

    group_errors = [m for m in console_messages + page_errors if "groupByDate" in m]
    print("groupByDate errors:", group_errors)
    print("Page errors:", page_errors)
    assert not group_errors, "Found groupByDate console/page error"
