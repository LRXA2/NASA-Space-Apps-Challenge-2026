// Check the production files through intercepted HTTP requests. No server or listening port is opened.
// Run after npm run build. Chrome is used by default; DEMO_BROWSER_CHANNEL can select another installed channel.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const app = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = resolve(app, "dist");
const data = resolve(dist, "data");
const origin = "http://127.0.0.1:49328";
const base = `${origin}/demo/`;
const patchRoute = "#/region/haworth/patch/r32-c32";
const analogRoute = `${patchRoute}/analogs`;
const json = async (file) => JSON.parse(await readFile(resolve(data, file), "utf8"));
const catalogue = await json("regions.json");
const earth = await json(catalogue.earth_file);
const environment = await json(catalogue.environment_file);
const analogs = await json("analogs/haworth.json");
const candidate = earth.candidates[analogs.tiles["r32-c32"].matches[1].candidate];
const pairRoute = `${analogRoute}/${encodeURIComponent(candidate.id)}`;
const sample = await readFile(resolve(data, environment.sample_input.file), "utf8");
const sampleLines = sample.trimEnd().split(/\r?\n/);
const header = sampleLines[0];
const sampleRow = (id) => {
  const row = sampleLines.slice(1).find((line) => line.split(",")[0] === id);
  assert.ok(row, `Missing sample row ${id}`);
  return row;
};
const csv = (rows, columns = header) => `${columns}\n${rows.join("\n")}\n`;
const selected = csv([sampleRow("eda_001"), sampleRow("eda_007"), sampleRow("dummy_003")]);
const mime = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".csv": "text/csv" };
const cases = new Map();

cases.set("data", async () => {
  assert.equal(catalogue.schema_version, 2);
  assert.equal(catalogue.regions.length, 7);
  assert.equal((await stat(resolve(data, earth.grid.file))).size, earth.grid.byte_length);
  const ids = new Set();
  let count = 0;
  for (const region of catalogue.regions) {
    const patches = await json(region.patches_file);
    const matches = await json(region.analogs_file);
    assert.equal(patches.patches.length, region.exported_patch_count);
    assert.equal((await stat(resolve(data, region.grid_file))).size, patches.grid.byte_length);
    for (const [index, patch] of patches.patches.entries()) {
      assert.ok(!ids.has(patch.tile_id), `Duplicate tile ${patch.tile_id}`);
      ids.add(patch.tile_id);
      assert.equal(patch.grid_offset, index * patches.grid.bytes_per_patch);
      const tile = matches.tiles[patch.slug];
      assert.equal(tile.tile_id, patch.tile_id);
      assert.equal(tile.query_id, patch.similarity_patch_id);
      assert.equal(tile.matches.length, 15);
      assert.deepEqual(tile.matches.map((match) => match.overall_rank), Array.from({ length: 15 }, (_, i) => i + 1));
      for (const match of tile.matches) {
        assert.ok(earth.candidates[match.candidate]);
        assert.equal(match.bands.length, 5);
        assert.equal(match.within.length, 5);
        assert.ok(Number.isFinite(match.cosine));
      }
      count += 1;
    }
  }
  assert.equal(count, 2910);
  // The T6 featured patches (src/featured.json) must still fit their kinds after a re-export.
  const featured = JSON.parse(await readFile(resolve(app, "src", "featured.json"), "utf8"));
  assert.deepEqual(Object.keys(featured).sort(), catalogue.regions.map((region) => region.slug).sort());
  for (const region of catalogue.regions) {
    const tiles = (await json(region.analogs_file)).tiles;
    const best = (kind) => tiles[featured[region.slug][kind]]?.matches[0];
    const inBand = (match) => match.within.filter(Boolean).length;
    assert.equal(inBand(best("strong")), 5, `${region.slug} strong pick`);
    assert.equal(inBand(best("misleading")), 0, `${region.slug} misleading pick`);
    assert.notEqual(earth.candidates[best("not_atacama").candidate].site, "atacama_san_pedro", `${region.slug} not-Atacama pick`);
  }
  assert.equal(environment.scenarios.filter((row) => row.kind === "artemis").length, 17);
  assert.equal(environment.scenarios.filter((row) => row.kind === "apollo").length, 6);
  for (const row of environment.scenarios) {
    for (const name of ["operations", "survival"]) {
      assert.ok(Array.isArray(row[name].gates));
      if (row[name].status !== "Pass") assert.equal(row[name].score, null);
    }
  }
  for (const file of [...environment.upload_files, environment.sample_input]) {
    const bytes = await readFile(resolve(data, file.file));
    assert.equal(createHash("sha256").update(bytes).digest("hex"), file.sha256, `Hash mismatch: ${file.file}`);
  }
  console.log(`  ${count} tiles, ${count * 15} matches, featured patches, and published scorer hashes checked`);
});

cases.set("routes", async (context) => {
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const route of ["#/", "#/region/haworth", patchRoute, analogRoute, pairRoute, "#/environment", "#/environment/eda_007", "#/environment/eda_008", "#/environment/apollo_11_mare_tranquillitatis_assumed", "#/upload"]) {
    await page.goto(base + route);
    await page.locator("h1").waitFor();
    await page.waitForFunction(() => !document.querySelector('[role="status"]')?.textContent?.startsWith("Loading"));
    assert.notEqual(await page.locator("h1").innerText(), "Page not found", route);
    assert.equal(
      await page.getByRole("contentinfo").getByRole("link", { name: "Source code", exact: true }).getAttribute("href"),
      "https://github.com/LRXA2/NASA-Space-Apps-Challenge-2026",
      `Source repository link: ${route}`,
    );
    if (route.includes("/analogs")) await page.locator("tbody tr").first().waitFor({ state: "attached" });
    const desktop = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    assert.deepEqual(desktop.violations.map(({ id, nodes }) => ({ id, nodes: nodes.length })), [], route);
    await page.setViewportSize({ width: 375, height: 812 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `Horizontal page overflow: ${route}`);
    const mobile = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    assert.deepEqual(mobile.violations.map(({ id, nodes }) => ({ id, nodes: nodes.length })), [], `Mobile ${route}`);
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  for (const route of ["#/region/missing", "#/region/haworth/patch/missing", `${analogRoute}/missing`, "#/missing"]) {
    await page.goto(base + route);
    await page.getByRole("heading", { name: /unavailable|not found/i }).waitFor();
  }
  await page.goto(base + "#/region/haworth");
  await page.getByRole("button", { name: "Next 50", exact: true }).click();
  await page.getByText("Page 2 of 17", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Previous 50", exact: true }).click();
  await page.getByText("Page 1 of 17", { exact: true }).waitFor();
  await page.locator('tbody a[href*="/patch/"]').first().click();
  await page.locator(".terrain-plot").first().waitFor();
  await page.goBack();
  await page.getByRole("button", { name: "Next 50", exact: true }).waitFor();
  await page.goForward();
  await page.locator(".terrain-plot").first().waitFor();
  await page.reload();
  await page.locator(".terrain-plot").first().waitFor();
  await page.goto(base + "#/region/haworth");
  await page.getByRole("heading", { name: "Three patches to start with" }).waitFor();
  assert.equal(await page.locator(".featured-list li").count(), 3);
  await page.locator(".featured-list .text-earth").first().waitFor();
  await page.locator(".featured-list li").first().getByRole("link").first().click();
  await page.locator(".terrain-plot").first().waitFor();
  await page.goto(base + "#/environment");
  await page.getByRole("heading", { name: "Environment checks for 17 potential landing regions" }).waitFor();
  assert.equal(await page.locator("tbody tr").count(), 23);
  await page.locator("caption").filter({ hasText: "Apollo landing sites, for comparison. Equatorial, not south-pole candidates" }).waitFor();
  await page.goto(base + "#/");
  const steps = await page.locator('.demo-path a').evaluateAll((links) => links.map((link) => link.getAttribute("href")));
  assert.equal(steps.length, 4);
  for (const [index, step] of steps.entries()) {
    await page.goto(base + step);
    await page.reload();
    await page.locator("h1").waitFor();
    assert.doesNotMatch(await page.locator("h1").innerText(), /unavailable|not found/i);
    await page.locator(index === 0 ? ".patch-table" : index === 2 ? ".earth-marker" : ".terrain-plot").first().waitFor();
  }
  assert.deepEqual(errors, []);
});

cases.set("interactions", async (context) => {
  const page = await context.newPage();
  await page.goto(base + analogRoute);
  await page.locator(".earth-marker").first().waitFor();
  const firstRowLink = page.locator("tbody tr").first().getByRole("link");
  await firstRowLink.focus();
  await page.locator(".earth-marker.is-active").waitFor();
  await page.locator(".earth-marker").nth(1).focus();
  await page.locator("tbody tr.is-active").waitFor();
  assert.equal(await page.locator(".earth-marker.is-active").count(), 1);
  await page.getByText("The basemap could not load.", { exact: false }).waitFor();
  assert.equal(await page.locator("tbody tr").count(), 15);
  await page.goto(base + pairRoute);
  await page.getByText("Show the checks as a table", { exact: true }).click();
  assert.equal(await page.locator(".checks-table tbody tr").count(), 5);
  const plot = page.locator(".terrain-plot").first();
  await plot.waitFor();
  await plot.focus();
  await plot.press("ArrowRight");
  await plot.press("ArrowDown");
  assert.equal(await page.locator(".terrain-cursor").count(), 4);
  for (const readout of await page.locator(".terrain-readout").allTextContents()) assert.match(readout, /Row 1, column 0:/);
  assert.equal(await page.locator(".distribution").count(), 2);
  const grids = await page.locator(".legend").allTextContents();
  assert.equal(grids[0], grids[1]);
  assert.equal(grids[2], grids[3]);
});

cases.set("missing-data", async (context) => {
  const page = await context.newPage();
  await page.route("**/data/grids/haworth.bin", (route) => route.fulfill({ status: 200, body: Buffer.alloc(4000) }));
  await page.goto(base + pairRoute);
  await page.getByText("Terrain grids are unavailable.", { exact: false }).waitFor();
  await page.getByText("Show the checks as a table", { exact: true }).click();
  assert.equal(await page.locator(".checks-table tbody tr").count(), 5);
  await page.unroute("**/data/grids/haworth.bin");
  await page.route("**/data/regions.json", (route) => route.fulfill({ status: 404, body: "Unavailable" }));
  await page.goto(base + "#/");
  await page.reload();
  await page.getByRole("heading", { name: "Region data is unavailable" }).waitFor();
});

cases.set("uploads", async (context) => {
  const page = await context.newPage();
  const pyodideLoads = [];
  context.on("request", (request) => {
    if (request.url().endsWith("/pyodide.mjs")) pyodideLoads.push(request.url());
  });
  await page.goto(base + "#/upload");
  const guide = page.locator(".input-guide");
  await guide.locator("summary").click();
  assert.deepEqual((await guide.locator("tbody code").allTextContents()).sort(), header.split(",").sort());
  await page.setViewportSize({ width: 375, height: 812 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), "Expanded input guide must fit the page");
  const guideAccessibility = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  assert.deepEqual(guideAccessibility.violations.map(({ id, nodes }) => ({ id, nodes: nodes.length })), []);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await guide.locator("summary").click();
  const input = page.locator("input[type=file]");
  await input.setInputFiles({ name: "three-cases.csv", mimeType: "text/csv", buffer: Buffer.from(selected) });
  await page.locator("caption").filter({ hasText: "Your 3 rows" }).waitFor({ timeout: 90000 });
  const results = page.getByRole("table", { name: /^Your 3 rows/ }).locator("tbody tr");
  assert.match(await results.nth(0).innerText(), /Pass/);
  assert.match(await results.nth(1).innerText(), /Fail/);
  assert.match(await results.nth(2).innerText(), /Unknown/);
  await results.first().locator("a, button").click();
  assert.equal(new URL(page.url()).hash, "#/upload", "Opening an uploaded row must not change the app route");
  assert.equal(await page.locator("details[open]").count(), 1);
  assert.ok(await page.locator("details[open] summary").evaluate((summary) => summary === document.activeElement));
  const accessibility = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  assert.deepEqual(accessibility.violations.map(({ id, nodes }) => ({ id, nodes: nodes.length })), []);
  const second = csv([sampleRow("eda_001")]);
  await input.setInputFiles({ name: "second.csv", mimeType: "text/csv", buffer: Buffer.from(second) });
  await page.locator("caption").filter({ hasText: "Your 1 rows" }).waitFor();
  assert.equal(pyodideLoads.length, 1, "Later uploads must reuse the worker");
  const fields = header.split(",");
  const badRange = sampleRow("eda_001").split(",");
  badRange[fields.indexOf("median_sun_visibility_fraction")] = "2";
  const invalid = [
    csv([sampleRow("eda_001"), sampleRow("eda_001")]),
    csv([`${sampleRow("eda_001")},1`], `${header},unexpected_column`),
    csv([badRange.join(",")]),
    `${header}\n`,
    `${header}\nonly-one-cell\n`,
  ];
  for (const [index, content] of invalid.entries()) {
    await input.setInputFiles({ name: `invalid-${index}.csv`, mimeType: "text/csv", buffer: Buffer.from(content) });
    await page.getByRole("alert").filter({ hasText: "could not be scored" }).waitFor();
    assert.equal(await page.getByRole("table", { name: /^Your \d+ rows/ }).count(), 0, "Invalid input must clear previous results");
  }
  console.log("  Input guide, Pass/Fail/Unknown, row navigation, worker reuse, and five invalid CSV cases checked");
});

if (process.argv[2] && !cases.has(process.argv[2])) throw new Error(`Unknown check: ${process.argv[2]}`);
const browser = await chromium.launch({ channel: process.env.DEMO_BROWSER_CHANNEL || "chrome", headless: true });
let failures = 0;
try {
  for (const [name, run] of cases) {
    if (process.argv[2] && process.argv[2] !== name) continue;
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: "block" });
    context.setDefaultTimeout(10000);
    await context.route(`${origin}/**`, async (route) => {
      const pathname = decodeURIComponent(new URL(route.request().url()).pathname);
      const file = resolve(dist, pathname.startsWith("/demo/") ? pathname.slice(6) || "index.html" : "__missing__");
      if (!file.startsWith(dist + sep)) return route.fulfill({ status: 404, body: "Not found" });
      try {
        await route.fulfill({ path: file, contentType: mime[extname(file)] || "application/octet-stream" });
      } catch {
        await route.fulfill({ status: 404, body: "Not found" });
      }
    });
    await context.route("https://tile.openstreetmap.org/**", (route) => route.abort());
    try {
      await run(context);
      console.log(`PASS ${name}`);
    } catch (error) {
      failures += 1;
      console.error(`FAIL ${name}: ${error.stack || error}`);
    } finally {
      await context.close();
    }
  }
} finally {
  await browser.close();
}
console.log(`Browser checks finished with ${failures} failure(s). No listening ports were opened.`);
process.exitCode = failures ? 1 : 0;
