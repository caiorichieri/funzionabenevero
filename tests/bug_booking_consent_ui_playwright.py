"""Playwright script body for MCP browser automation.

Focused UI check: public therapist slot -> BookingSheet register mode ->
local privacy/terms validation -> /auth/register payload includes both booleans -> OTP step.

The same code body below was pasted into `mcp_browser_automation` on July 2026.
It is saved as a test artifact for reproducibility; the MCP harness provides `page`.
"""

import json
import time

await page.set_viewport_size({"width": 1920, "height": 1080})
result = {"checks": [], "register_payloads": [], "register_responses": []}
try:
    await page.context.clear_cookies()
    await page.goto("https://portugues-writer-2.preview.emergentagent.com/terapeuti/69e5c83da585e313092bd595", wait_until="networkidle", timeout=30000)
    print("Opened therapist public profile")
    result["checks"].append({"name": "profile_opened", "passed": True})

    cookie_btn = page.get_by_test_id("cookie-reject-all-btn")
    if await cookie_btn.count() > 0:
        await cookie_btn.click(force=True)
        await page.wait_for_timeout(300)
        print("Dismissed cookie banner")

    await page.get_by_test_id("therapist-public").wait_for(timeout=15000)
    slot = page.locator("button[data-testid^='slot-btn-']:not([disabled])").first
    await slot.scroll_into_view_if_needed()
    await slot.click(force=True)
    print("Clicked first available slot")
    await page.get_by_test_id("booking-sheet").wait_for(timeout=10000)
    await page.get_by_test_id("booking-continue").evaluate("el => el.click()")
    await page.get_by_test_id("step-auth").wait_for(timeout=10000)
    print("BookingSheet auth/register step visible")

    def on_request(request):
        if "/api/auth/register" in request.url and request.method == "POST":
            payload = request.post_data or ""
            try:
                result["register_payloads"].append(json.loads(payload))
            except Exception:
                result["register_payloads"].append(payload)

    async def on_response(response):
        if "/api/auth/register" in response.url and response.request.method == "POST":
            try:
                body = await response.json()
            except Exception:
                body = await response.text()
            result["register_responses"].append({"status": response.status, "body": body})

    page.on("request", on_request)
    page.on("response", on_response)

    email = f"qa.booking.ui.{int(time.time())}@funzionabene.it"
    result["email"] = email
    await page.get_by_test_id("booking-nome").fill("QA")
    await page.get_by_test_id("booking-cognome").fill("UI")
    await page.get_by_test_id("booking-email").fill(email)
    await page.get_by_test_id("booking-password").fill("Password123!")

    # Negative edge case: privacy/terms checkbox not selected -> local error, no API call.
    before_count = len(result["register_payloads"])
    await page.get_by_test_id("booking-auth-submit").evaluate("el => el.click()")
    await page.wait_for_timeout(800)
    error_text = await page.evaluate("""() => {
const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
return errorElements.map(el => el.textContent).join(", ");
}""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")
    visible_error = await page.get_by_test_id("booking-error").inner_text(timeout=5000)
    no_api_call = len(result["register_payloads"]) == before_count
    result["checks"].append({
        "name": "unchecked_privacy_terms_shows_local_error_and_no_api_call",
        "passed": "Devi accettare Privacy Policy e Termini di Servizio" in visible_error and no_api_call,
        "visible_error": visible_error,
        "api_call_count_before": before_count,
        "api_call_count_after": len(result["register_payloads"]),
    })
    print("Unchecked checkbox validation result:", result["checks"][-1])

    # Positive path: same checkbox represents both privacy and terms; payload must include both true.
    await page.get_by_test_id("booking-privacy").check(force=True)
    async with page.expect_response(lambda r: "/api/auth/register" in r.url and r.request.method == "POST", timeout=20000) as resp_info:
        await page.get_by_test_id("booking-auth-submit").evaluate("el => el.click()")
    resp = await resp_info.value
    print("Register response status", resp.status)
    await page.get_by_test_id("step-otp").wait_for(timeout=15000)
    otp_text = await page.get_by_test_id("otp-dev").inner_text(timeout=5000)
    payload = result["register_payloads"][-1] if result["register_payloads"] else {}
    result["checks"].append({
        "name": "checked_privacy_terms_registers_payload_has_both_consents_and_advances_to_otp",
        "passed": (
            resp.status == 200
            and isinstance(payload, dict)
            and payload.get("consenso_privacy") is True
            and payload.get("consenso_termini") is True
            and "codice OTP" in otp_text
            and "I consensi obbligatori" not in " ".join([str(x) for x in result["register_responses"]])
        ),
        "payload": payload,
        "otp_text": otp_text,
        "register_responses": result["register_responses"],
    })
    print("Positive registration result:", result["checks"][-1])

except Exception as e:
    result["exception"] = str(e)
    print("TEST FAILED WITH EXCEPTION", str(e))
finally:
    result["passed"] = all(c.get("passed") for c in result.get("checks", [])) and "exception" not in result
    with open("/app/test_reports/booking_consent_ui_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Final UI result:", json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise Exception("Booking consent UI test failed")
