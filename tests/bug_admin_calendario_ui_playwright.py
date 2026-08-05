"""Focused Playwright steps for /admin/calendario bug verification.

This script body is executed by the browser automation harness with an existing
async `page` object. It verifies that August 2026 admin calendar renders both
booking-only and draft-availability days, and that the drill-down contains the
expected booking/therapist details.
"""

await page.set_viewport_size({"width": 1920, "height": 1080})
try:
    print("Step 1: open login page")
    await page.goto("https://portugues-writer-2.preview.emergentagent.com/login", wait_until="domcontentloaded")
    await page.get_by_test_id("login-email").fill("admin@funzionabene.it")
    await page.get_by_test_id("login-password").fill("admin2026")
    await page.get_by_test_id("login-submit").click()
    await page.wait_for_url("**/admin", timeout=20000)
    print("PASS: admin login succeeded")

    print("Step 2: open admin calendar and navigate to August 2026")
    await page.goto("https://portugues-writer-2.preview.emergentagent.com/admin/calendario", wait_until="domcontentloaded")
    await page.get_by_test_id("admin-calendario-page").wait_for(timeout=20000)
    for _ in range(36):
        heading = (await page.locator("h2").inner_text()).strip()
        if heading == "Agosto 2026":
            break
        if "2026" in heading and any(m in heading for m in ["Settembre", "Ottobre", "Novembre", "Dicembre"]):
            await page.get_by_test_id("prev-month").click()
        elif "2027" in heading or "2028" in heading:
            await page.get_by_test_id("prev-month").click()
        else:
            await page.get_by_test_id("next-month").click()
        await page.wait_for_timeout(300)
    final_heading = (await page.locator("h2").inner_text()).strip()
    assert final_heading == "Agosto 2026", f"Could not reach Agosto 2026, at {final_heading}"
    await page.get_by_test_id("admin-day-2026-08-06").wait_for(timeout=20000)
    print("PASS: August 2026 calendar loaded")

    print("Step 3: verify legend and totals")
    page_text = await page.get_by_test_id("admin-calendario-page").inner_text()
    assert "Solo prenotazioni" in page_text
    assert "2 giorni attivi" in page_text
    assert "2 slot" in page_text
    assert "1 prenotazioni" in page_text
    print("PASS: legend and totals include bookings")

    print("Step 4: verify booking-only day 2026-08-06")
    day_806 = page.get_by_test_id("admin-day-2026-08-06")
    assert await day_806.is_enabled()
    text_806 = await day_806.inner_text()
    class_806 = await day_806.get_attribute("class")
    assert "1 pren." in text_806, f"Missing booking badge in day 806 text: {text_806}"
    assert "bg-[#D4A017]/25" in class_806, f"Booking-only day not gold: {class_806}"
    await day_806.click()
    await page.get_by_test_id("admin-day-detail").wait_for(timeout=10000)
    detail_806 = await page.get_by_test_id("admin-day-detail").inner_text()
    assert "Prenotazioni" in detail_806
    assert "Luca Bianchi" in detail_806
    assert "con Maria Rossi" in detail_806
    assert "15:00" in detail_806
    assert "confermato" in detail_806
    assert "0 disponibili · 0 slot" in detail_806
    print("PASS: booking-only day details rendered")

    print("Step 5: verify draft availability day 2026-08-07")
    day_807 = page.get_by_test_id("admin-day-2026-08-07")
    assert await day_807.is_enabled()
    text_807 = await day_807.inner_text()
    class_807 = await day_807.get_attribute("class")
    assert "1" in text_807, f"Missing therapist count on 807: {text_807}"
    assert "bg-green-100" in class_807, f"Availability day not green: {class_807}"
    await day_807.click()
    await page.get_by_test_id("admin-day-detail").wait_for(timeout=10000)
    detail_807 = await page.get_by_test_id("admin-day-detail").inner_text()
    assert "Disponibilità pubblicate" in detail_807
    assert "Maria Rossi" in detail_807
    assert "bozza" in detail_807
    assert "14:00" in detail_807 and "15:00" in detail_807
    assert "1 disponibili · 2 slot" in detail_807
    print("PASS: draft availability day details rendered")

    error_text = await page.evaluate("""() => {
const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
return errorElements.map(el => el.textContent).join(", ");
}""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")
    print("UI BUG VERIFICATION PASSED")
except Exception as exc:
    print(f"UI BUG VERIFICATION FAILED: {exc}")
    error_text = await page.evaluate("""() => {
const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
return errorElements.map(el => el.textContent).join(", ");
}""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")
    raise