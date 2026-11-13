import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { access, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test, { after, before } from "node:test";

const templateRoot = new URL("../", import.meta.url);
const projectRoot = fileURLToPath(templateRoot);
const serverOrigin = "http://127.0.0.1:4173";
let serverProcess;
let serverOutput = "";

before(async () => {
  const executable = join(projectRoot, "node_modules", ".bin", "wrangler");
  serverProcess = spawn(
    executable,
    ["dev", "--config", "wrangler.json", "--port", "4173", "--ip", "127.0.0.1"],
    {
      cwd: join(projectRoot, "dist", "server"),
      env: { ...process.env, WRANGLER_SEND_METRICS: "false" },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  serverProcess.stdout.on("data", (chunk) => { serverOutput += chunk.toString(); });
  serverProcess.stderr.on("data", (chunk) => { serverOutput += chunk.toString(); });

  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (serverProcess.exitCode !== null) {
      throw new Error(`Wrangler exited before the server was ready.\n${serverOutput}`);
    }
    try {
      const response = await fetch(`${serverOrigin}/`);
      if (response.ok) return;
    } catch {
      // The local Worker is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for the local Worker.\n${serverOutput}`);
}, { timeout: 30_000 });

after(async () => {
  if (!serverProcess || serverProcess.exitCode !== null) return;
  serverProcess.kill("SIGTERM");
  await Promise.race([
    new Promise((resolve) => serverProcess.once("exit", resolve)),
    new Promise((resolve) => setTimeout(resolve, 3_000)),
  ]);
});

async function render() {
  return fetch(`${serverOrigin}/`, { headers: { accept: "text/html" } });
}

test("server-renders the BayRoute dashboard shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>BayRoute \| Transit reliability intelligence<\/title>/i);
  assert.match(html, /Know the delay/);
  assert.match(html, /South Bay transit intelligence/);
  assert.match(html, /Routes monitored/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/i);
});

test("removes starter assets and includes the product implementation", async () => {
  const [css, page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(packageJson, /"maplibre-gl"/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  assert.match(css, /\.transit-map/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(page, /<Dashboard \/>/);
  assert.match(layout, /BayRoute \| Transit reliability intelligence/);
  assert.doesNotMatch(layout, /codex-preview|_sites-preview|Starter Project/);

  await assert.rejects(
    access(new URL("app/_sites-preview", templateRoot)),
  );
});
