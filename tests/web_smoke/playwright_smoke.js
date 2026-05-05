import { chromium } from "../../web/node_modules/@playwright/test/index.mjs";

const baseURL = process.env.MINDFORGE_WEB_URL || "http://127.0.0.1:8765";

const browser = await chromium.launch();
const page = await browser.newPage();

async function assertVisible(text) {
  const locator = page.getByText(text, { exact: false }).first();
  await locator.waitFor({ timeout: 5000 });
}

await page.goto(baseURL, { waitUntil: "networkidle" });
await assertVisible("Local only");
await assertVisible("Home");
await assertVisible("Provider");

await page.getByRole("button", { name: "Setup", exact: true }).click();
await assertVisible("Configuration checklist");

await page.getByRole("button", { name: "Sources", exact: true }).click();
await assertVisible("Sources");

await page.getByRole("button", { name: "Drafts", exact: true }).click();
await assertVisible("Drafts");
const empty = page.getByText("No drafts waiting for review", { exact: false });
const approveButton = page.getByRole("button", { name: "Approve...", exact: true });
if (await empty.count()) {
  await empty.first().waitFor({ timeout: 5000 });
} else {
  await page.getByRole("checkbox").check();
  await approveButton.click();
  await assertVisible("Second confirmation required");
}

await page.getByRole("button", { name: "Recall", exact: true }).click();
await assertVisible("Recall / Knowledge");

const rawTraceback = await page.getByText("Traceback (most recent call last)", { exact: false }).count();
if (rawTraceback > 0) {
  throw new Error("Raw traceback is visible in the UI");
}

await browser.close();
