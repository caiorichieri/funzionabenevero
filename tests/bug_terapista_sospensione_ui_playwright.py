"""Playwright body used by mcp_browser_automation for therapist suspension UI flow."""

# This file is an artifact of the focused bug verification. The browser tool
# executes the same body inside an async function with a `page` object.

import asyncio

THERAPIST_ID = "69e5c83ca585e313092bd593"
BASE_URL = "https://portugues-writer-2.preview.emergentagent.com"

try:
    await page.set_viewport_size({"width": 1920, "height": 1080})
    print("Step 1: viewport set")

    async def handle_dialog(dialog):
        print(f"Dialog accepted: {dialog.message}")
        await dialog.accept()

    page.on("dialog", lambda dialog: asyncio.create_task(handle_dialog(dialog)))

    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.locator('[data-testid="login-email"]').fill("admin@funzionabene.it")
    await page.locator('[data-testid="login-password"]').fill("admin2026")
    await page.locator('[data-testid="login-submit"]').click()
    await page.wait_for_url("**/admin", timeout=15000)
    print("Step 2: admin login succeeded")

    await page.goto(f"{BASE_URL}/admin/terapisti", wait_until="networkidle")
    await page.locator('[data-testid="terapisti-search"]').fill("Maria Rossi")
    row = page.locator(f'[data-testid="terapista-row-{THERAPIST_ID}"]')
    await row.wait_for(state="visible", timeout=15000)
    print("Step 3: Maria Rossi row visible")

    # Existing non-destructive action buttons are still present on the row.
    await row.locator(f'[data-testid="toggle-verifica-{THERAPIST_ID}"]').wait_for(state="visible", timeout=5000)
    await row.locator(f'[data-testid="edit-terapista-{THERAPIST_ID}"]').wait_for(state="visible", timeout=5000)
    await row.locator(f'[data-testid="delete-terapista-{THERAPIST_ID}"]').wait_for(state="visible", timeout=5000)
    print("Step 4: existing Verifica/Edit/Delete buttons present")

    badge = row.locator(f'[data-testid="badge-sospeso-{THERAPIST_ID}"]')
    if await badge.count() and await badge.is_visible():
        print("Initial state was suspended; reactivating first to normalize")
        await row.locator(f'[data-testid="toggle-sospensione-{THERAPIST_ID}"]').click()
        await page.wait_for_timeout(1200)
        await badge.wait_for(state="detached", timeout=10000)
        await row.wait_for(state="visible", timeout=10000)

    toggle = row.locator(f'[data-testid="toggle-sospensione-{THERAPIST_ID}"]')
    title_before = await toggle.get_attribute("title")
    if title_before != "Sospendi terapista":
        raise AssertionError(f"Expected initial suspension button title, got {title_before}")
    print("Step 5: pause/suspend button visible with expected title")

    await toggle.click()
    await page.wait_for_timeout(1500)
    await row.locator(f'[data-testid="badge-sospeso-{THERAPIST_ID}"]').wait_for(state="visible", timeout=10000)
    title_after_suspend = await row.locator(f'[data-testid="toggle-sospensione-{THERAPIST_ID}"]').get_attribute("title")
    if title_after_suspend != "Riattiva terapista":
        raise AssertionError(f"Expected play/reactivate title after suspension, got {title_after_suspend}")
    print("Step 6: after suspend, SOSPESO badge visible and button changed to reactivate/play")

    await row.locator(f'[data-testid="toggle-sospensione-{THERAPIST_ID}"]').click()
    await page.wait_for_timeout(1500)
    await row.locator(f'[data-testid="badge-sospeso-{THERAPIST_ID}"]').wait_for(state="detached", timeout=10000)
    title_after_reactivate = await row.locator(f'[data-testid="toggle-sospensione-{THERAPIST_ID}"]').get_attribute("title")
    if title_after_reactivate != "Sospendi terapista":
        raise AssertionError(f"Expected pause/suspend title after reactivation, got {title_after_reactivate}")
    print("Step 7: after reactivate, SOSPESO badge gone and button changed back to suspend/pause")

    error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")

    print("UI_TEST_RESULT: PASS")
except Exception as e:
    print(f"UI_TEST_RESULT: FAIL - {repr(e)}")
    raise