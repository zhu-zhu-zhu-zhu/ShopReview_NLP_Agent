import { access, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_DIR = path.resolve(SCRIPT_DIR, "..", "..");
const OUTPUT_DIR = path.join(PROJECT_DIR, "screenshots", "dashboard");
const DEFAULT_URL = "http://127.0.0.1:5173";
// Keep the layout from the user's browser capture, but render at 2× pixel
// density so dashboard text, chart axes, and thin borders stay sharp in reports.
const VIEWPORT = { width: 1440, height: 687 };
const DEVICE_SCALE_FACTOR = 2;
const OUTPUT_PIXELS = {
  width: Math.round(VIEWPORT.width * DEVICE_SCALE_FACTOR),
  height: Math.round(VIEWPORT.height * DEVICE_SCALE_FACTOR),
};

function readArgument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

async function findBrowser() {
  const candidates = [
    process.env.CHROME_PATH,
    process.env.PLAYWRIGHT_CHROME_PATH,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);

  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Try the next locally installed Chromium browser.
    }
  }
  throw new Error(
    "未找到 Chrome 或 Edge。可通过 CHROME_PATH 指定浏览器可执行文件。",
  );
}

async function assertService(url, label) {
  let response;
  try {
    response = await fetch(url, { signal: AbortSignal.timeout(8_000) });
  } catch (error) {
    throw new Error(`${label} 不可访问：${url}（${error.message}）`);
  }
  if (!response.ok) {
    throw new Error(`${label} 返回 HTTP ${response.status}：${url}`);
  }
}

async function main() {
  const dashboardUrl = readArgument("--url", DEFAULT_URL).replace(/\/+$/, "");
  const healthUrl = readArgument("--health-url", "http://127.0.0.1:8080/api/health");
  const browserPath = await findBrowser();

  await assertService(healthUrl, "Warehouse 后端");
  await assertService(dashboardUrl, "可视化大屏");
  await mkdir(OUTPUT_DIR, { recursive: true });

  const browser = await chromium.launch({
    executablePath: browserPath,
    headless: true,
    args: ["--disable-gpu-sandbox", "--font-render-hinting=none"],
  });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: DEVICE_SCALE_FACTOR,
    locale: "zh-CN",
    reducedMotion: "reduce",
    colorScheme: "dark",
  });
  const page = await context.newPage();
  const browserErrors = [];
  const failedResponses = [];

  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400 && response.url().includes("/api/")) {
      failedResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  const captures = [];
  const capturePage = async (file, title) => {
    await page.screenshot({
      path: path.join(OUTPUT_DIR, file),
      fullPage: false,
      animations: "disabled",
    });
    captures.push({ file, title, type: "viewport" });
    console.log(`[CAPTURED] ${file} - ${title}`);
  };
  const captureElement = async (file, title, selector) => {
    const target = page.locator(selector).first();
    await target.waitFor({ state: "visible", timeout: 15_000 });
    await target.scrollIntoViewIfNeeded();
    await page.waitForTimeout(250);
    await target.screenshot({
      path: path.join(OUTPUT_DIR, file),
      animations: "disabled",
    });
    captures.push({ file, title, type: "component", selector });
    console.log(`[CAPTURED] ${file} - ${title}`);
  };

  try {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "reviewops-launcher-position-v1",
        JSON.stringify({ left: 1231, top: 93 }),
      );
    });
    await page.goto(dashboardUrl, {
      waitUntil: "networkidle",
      timeout: 45_000,
    });
    await page.locator(".wall").waitFor({ state: "visible", timeout: 20_000 });
    await page.getByText("99,703", { exact: true }).first().waitFor({
      state: "visible",
      timeout: 20_000,
    });
    await page.waitForTimeout(1_200);
    await page.addStyleTag({
      content: `
        *, *::before, *::after {
          caret-color: transparent !important;
          animation-play-state: paused !important;
        }
      `,
    });

    await page.getByRole("tab", { name: "近 365 日" }).click();
    await page.waitForTimeout(700);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await capturePage(
      "01-dashboard-overview.png",
      "生产数据可视化大屏总览（差评榜 / 近 365 日）",
    );

    await page.getByRole("tab", { name: "好评榜" }).click();
    await page.waitForTimeout(500);
    await captureElement(
      "02-positive-rankings.png",
      "店铺好评榜与商品好评榜",
      'section[aria-label="风险热力榜"]',
    );

    await page.getByRole("tab", { name: "近 365 日" }).click();
    await page.waitForTimeout(700);
    await captureElement(
      "03-sentiment-trend-365d.png",
      "近 365 日情感时间河",
      'section[aria-label="情感时间河"]',
    );

    await captureElement(
      "04-alert-radar.png",
      "生产告警雷达",
      'section[aria-label="告警雷达"]',
    );

    await captureElement(
      "05-model-diagnostics.png",
      "星级预测矩阵、置信度和负面方面诊断",
      'section[aria-label="模型诊断"]',
    );

    await page.getByRole("button", { name: "AI 风险调查，可拖动位置" }).click();
    await page.locator("#reviewops-drawer").waitFor({ state: "visible" });
    await page.waitForTimeout(350);
    await capturePage(
      "06-agent-drawer.png",
      "ReviewOps Copilot 快捷调查与自然语言入口",
    );

    await page.getByRole("button", { name: "调查最高风险商品" }).click();
    await page.locator(".investigation-result").waitFor({
      state: "visible",
      timeout: 30_000,
    });
    await page.waitForTimeout(500);
    await page.locator("#reviewops-drawer").evaluate((drawer) => {
      const result = drawer.querySelector(".investigation-result");
      if (!(result instanceof HTMLElement)) return;
      drawer.scrollTo({
        top: Math.max(0, result.offsetTop - 92),
        behavior: "instant",
      });
    });
    await page.waitForTimeout(250);
    await captureElement(
      "07-agent-risk-investigation.png",
      "最高风险商品真实 warehouse 证据链",
      "#reviewops-drawer",
    );

    if (browserErrors.length || failedResponses.length) {
      const details = [
        ...browserErrors.map((item) => `console: ${item}`),
        ...failedResponses.map((item) => `response: ${item}`),
      ].join("\n");
      throw new Error(`浏览器验证发现错误：\n${details}`);
    }

    const manifest = {
      generated_at: new Date().toISOString(),
      source_url: dashboardUrl,
      health_url: healthUrl,
      data_contract: {
        data_mode: "warehouse",
        load_batch_id: "prod_v1_100k",
        model_version: "tfidf_logreg_oof_v1",
        review_count: 99703,
      },
      viewport: VIEWPORT,
      device_scale_factor: DEVICE_SCALE_FACTOR,
      output_pixels: OUTPUT_PIXELS,
      browser: browserPath,
      screenshots: captures,
      validation: {
        browser_console_errors: 0,
        failed_api_responses: 0,
      },
    };
    await writeFile(
      path.join(OUTPUT_DIR, "manifest.json"),
      `${JSON.stringify(manifest, null, 2)}\n`,
      "utf8",
    );
    console.log(`DASHBOARD SCREENSHOT RESULT: PASS (${captures.length} files)`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`DASHBOARD SCREENSHOT RESULT: FAIL\n${error.stack || error}`);
  process.exitCode = 1;
});
