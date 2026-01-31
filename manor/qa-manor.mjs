import { chromium } from "playwright";

const BASE = "http://localhost:3000";
const API = "http://localhost:8700";

const results = [];

function log(page, status, msg) {
  const icon = status === "PASS" ? "✓" : status === "FAIL" ? "✗" : "⚠";
  const line = `${icon} [${page}] ${msg}`;
  console.log(line);
  results.push({ page, status, msg });
}

async function testPage(browserPage, name, path, checks) {
  try {
    const response = await browserPage.goto(`${BASE}${path}`, {
      waitUntil: "networkidle",
      timeout: 15000,
    });
    if (!response || response.status() !== 200) {
      log(name, "FAIL", `HTTP ${response?.status() || "no response"} on ${path}`);
      return;
    }
    log(name, "PASS", `Page loads (HTTP 200)`);

    // Check for React errors / Next.js error overlay
    const errorOverlay = await browserPage
      .locator('[data-nextjs-dialog], [data-nextjs-container], .nextjs-container-errors-header')
      .count();
    if (errorOverlay > 0) {
      const errorText = await browserPage.locator('[data-nextjs-dialog], [data-nextjs-container]').first().textContent();
      log(name, "FAIL", `Next.js error overlay: ${errorText?.slice(0, 200)}`);
      return;
    }

    // Check for console errors
    const consoleErrors = [];
    browserPage.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    // Run page-specific checks
    if (checks) {
      await checks(browserPage, name);
    }

    // Check for unhandled errors in console (API fetch failures etc)
    await browserPage.waitForTimeout(1000);
    const apiErrors = consoleErrors.filter(
      (e) => e.includes("API") || e.includes("fetch") || e.includes("Failed")
    );
    if (apiErrors.length > 0) {
      log(name, "WARN", `Console errors: ${apiErrors.slice(0, 3).join("; ").slice(0, 200)}`);
    }
  } catch (err) {
    log(name, "FAIL", `${err.message.slice(0, 200)}`);
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  // Collect all console errors globally
  const allConsoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") allConsoleErrors.push({ url: page.url(), text: msg.text() });
  });

  // ── Dashboard ──────────────────────────────────────────────
  await testPage(page, "Dashboard", "/", async (p, name) => {
    const sidebar = await p.locator("nav").count();
    if (sidebar > 0) log(name, "PASS", "Sidebar renders");
    else log(name, "FAIL", "Sidebar missing");

    const heading = await p.locator("h1, h2, h3").first().textContent();
    log(name, "PASS", `Main heading: "${heading?.trim().slice(0, 60)}"`);

    // Check amber theming
    const html = await p.content();
    if (html.includes("amber")) log(name, "PASS", "Amber theme classes present");
    else log(name, "WARN", "No amber theme classes found");
  });

  // ── Chat ───────────────────────────────────────────────────
  await testPage(page, "Chat", "/chat", async (p, name) => {
    // Check for input area
    const textarea = await p.locator("textarea, input[type=text]").count();
    if (textarea > 0) log(name, "PASS", "Chat input present");
    else log(name, "FAIL", "Chat input missing");
  });

  // ── Sessions ───────────────────────────────────────────────
  await testPage(page, "Sessions", "/sessions", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Session") || content.includes("session") || content.includes("Create") || content.includes("No")) {
      log(name, "PASS", "Sessions content renders");
    } else {
      log(name, "FAIL", "Sessions page appears empty");
    }
  });

  // ── Tasks ──────────────────────────────────────────────────
  await testPage(page, "Tasks", "/tasks", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Task") || content.includes("task") || content.includes("No") || content.includes("Create")) {
      log(name, "PASS", "Tasks content renders");
    } else {
      log(name, "FAIL", "Tasks page appears empty");
    }
  });

  // ── Logs ───────────────────────────────────────────────────
  await testPage(page, "Logs", "/logs", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Log") || content.includes("log") || content.includes("No") || content.includes("Filter")) {
      log(name, "PASS", "Logs content renders");
    } else {
      log(name, "FAIL", "Logs page appears empty");
    }
  });

  // ── Skills ─────────────────────────────────────────────────
  await testPage(page, "Skills", "/skills", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Skill") || content.includes("skill") || content.includes("No") || content.includes("Create")) {
      log(name, "PASS", "Skills content renders");
    } else {
      log(name, "FAIL", "Skills page appears empty");
    }
  });

  // ── Lore ───────────────────────────────────────────────────
  await testPage(page, "Lore", "/lore", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("soul") || content.includes("claude") || content.includes("Lore") || content.includes("lore")) {
      log(name, "PASS", "Lore content renders (files visible)");
    } else {
      log(name, "WARN", "Lore page may not be showing files");
    }
  });

  // ── Scratchpad ─────────────────────────────────────────────
  await testPage(page, "Scratchpad", "/scratchpad", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Scratchpad") || content.includes("scratchpad") || content.includes("No") || content.includes("Create")) {
      log(name, "PASS", "Scratchpad content renders");
    } else {
      log(name, "FAIL", "Scratchpad page appears empty");
    }
  });

  // ── Jobs ───────────────────────────────────────────────────
  await testPage(page, "Jobs", "/jobs", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Job") || content.includes("job") || content.includes("Schedule") || content.includes("No") || content.includes("Create")) {
      log(name, "PASS", "Jobs content renders");
    } else {
      log(name, "FAIL", "Jobs page appears empty");
    }
  });

  // ── System ─────────────────────────────────────────────────
  await testPage(page, "System", "/system", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("System") || content.includes("Health") || content.includes("system") || content.includes("Monitor")) {
      log(name, "PASS", "System content renders");
    } else {
      log(name, "FAIL", "System page appears empty");
    }
  });

  // ── Config ─────────────────────────────────────────────────
  await testPage(page, "Config", "/config", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Config") || content.includes("config") || content.includes("Agent") || content.includes("Setting")) {
      log(name, "PASS", "Config content renders");
    } else {
      log(name, "FAIL", "Config page appears empty");
    }
  });

  // ── Outbox ─────────────────────────────────────────────────
  await testPage(page, "Outbox", "/outbox", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Outbox") || content.includes("outbox") || content.includes("Message") || content.includes("No")) {
      log(name, "PASS", "Outbox content renders");
    } else {
      log(name, "FAIL", "Outbox page appears empty");
    }
  });

  // ── Events ─────────────────────────────────────────────────
  await testPage(page, "Events", "/events", async (p, name) => {
    const content = await p.textContent("body");
    if (content.includes("Event") || content.includes("event") || content.includes("No") || content.includes("Topic")) {
      log(name, "PASS", "Events content renders");
    } else {
      log(name, "FAIL", "Events page appears empty");
    }
  });

  // ── API Endpoints Spot Check ───────────────────────────────
  console.log("\n── API Endpoint Checks ──");
  const apiChecks = [
    ["/health", "Health"],
    ["/health/detailed", "Health Detailed"],
    ["/metrics", "Metrics"],
    ["/api/sessions", "Sessions API"],
    ["/api/logs?limit=5", "Logs API"],
    ["/api/skills", "Skills API"],
    ["/api/lore", "Lore API"],
    ["/api/scratchpad", "Scratchpad API"],
    ["/api/tasks", "Tasks API"],
    ["/api/jobs", "Jobs API"],
    ["/api/config", "Config API"],
    ["/api/agents", "Agents API"],
    ["/api/events", "Events API"],
    ["/api/outbox", "Outbox API"],
    ["/api/tasks/summary", "Tasks Summary"],
    ["/api/jobs/summary", "Jobs Summary"],
    ["/api/logs/summary", "Logs Summary"],
  ];

  for (const [endpoint, label] of apiChecks) {
    try {
      const resp = await page.request.get(`${API}${endpoint}`);
      if (resp.ok()) {
        const body = await resp.json();
        log(label, "PASS", `API ${endpoint} → ${JSON.stringify(body).slice(0, 100)}`);
      } else {
        const text = await resp.text();
        log(label, "FAIL", `API ${endpoint} → HTTP ${resp.status()}: ${text.slice(0, 100)}`);
      }
    } catch (err) {
      log(label, "FAIL", `API ${endpoint} → ${err.message.slice(0, 100)}`);
    }
  }

  // ── Navigation Test ────────────────────────────────────────
  console.log("\n── Navigation Test ──");
  await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
  const navLinks = await page.locator("nav a[href]").all();
  log("Navigation", "PASS", `Sidebar has ${navLinks.length} links`);

  for (const link of navLinks) {
    const href = await link.getAttribute("href");
    if (href && href.startsWith("/")) {
      await link.click();
      await page.waitForTimeout(500);
      const currentUrl = page.url();
      if (currentUrl.includes(href)) {
        log("Navigation", "PASS", `Click → ${href} works`);
      } else {
        log("Navigation", "WARN", `Click → ${href} landed on ${currentUrl}`);
      }
    }
  }

  // ── Summary ────────────────────────────────────────────────
  console.log("\n═══════════════════════════════════════");
  const passes = results.filter((r) => r.status === "PASS").length;
  const fails = results.filter((r) => r.status === "FAIL").length;
  const warns = results.filter((r) => r.status === "WARN").length;
  console.log(`RESULTS: ${passes} PASS, ${fails} FAIL, ${warns} WARN`);

  if (fails > 0) {
    console.log("\nFAILURES:");
    results
      .filter((r) => r.status === "FAIL")
      .forEach((r) => console.log(`  ✗ [${r.page}] ${r.msg}`));
  }
  if (warns > 0) {
    console.log("\nWARNINGS:");
    results
      .filter((r) => r.status === "WARN")
      .forEach((r) => console.log(`  ⚠ [${r.page}] ${r.msg}`));
  }

  if (allConsoleErrors.length > 0) {
    console.log(`\nCONSOLE ERRORS (${allConsoleErrors.length}):`);
    // dedupe by text
    const seen = new Set();
    allConsoleErrors.forEach((e) => {
      const key = e.text.slice(0, 100);
      if (!seen.has(key)) {
        seen.add(key);
        console.log(`  [${new URL(e.url).pathname}] ${e.text.slice(0, 200)}`);
      }
    });
  }

  console.log("\n═══════════════════════════════════════");

  await browser.close();
}

main().catch((err) => {
  console.error("QA script crashed:", err);
  process.exit(1);
});
