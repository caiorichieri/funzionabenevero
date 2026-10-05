const puppeteer = require("puppeteer-core");
(async () => {
  const browser = await puppeteer.launch({
    executablePath: "/usr/bin/chromium",
    headless: "new",
    args: ["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-web-security","--disable-features=IsolateOrigins,site-per-process"],
  });
  const page = await browser.newPage();
  await page.setUserAgent("ReactSnap");
  await page.setViewport({ width: 1280, height: 900 });
  await page.setRequestInterception(true);
  page.on("request", (req) => {
    const u = req.url();
    if (/posthog|google-analytics|googletagmanager|facebook\.net|clarity\.ms|linkedin|tiktok/i.test(u)) req.abort();
    else req.continue();
  });
  page.on("console", m => console.log("[CONSOLE]", m.type(), m.text().substring(0,200)));
  page.on("pageerror", e => console.log("[PAGEERROR]", e.message));
  page.on("requestfailed", r => console.log("[REQFAIL]", r.url().substring(0,120), r.failure().errorText));
  try {
    await page.goto("http://127.0.0.1:4747/", { waitUntil: "networkidle0", timeout: 30000 });
    await new Promise(r => setTimeout(r, 800));
    const info = await page.evaluate(() => ({
      hasRoot: !!document.getElementById("root"),
      rootKids: document.getElementById("root")?.children.length ?? -1,
      rootInner: document.getElementById("root")?.innerHTML.length ?? -1,
      bodyKids: document.body.children.length,
      href: location.href,
    }));
    console.log("INFO:", JSON.stringify(info));
  } catch (e) { console.log("GOTO err:", e.message); }
  await browser.close();
})();
