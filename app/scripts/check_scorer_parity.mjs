// Run the published environment scorer in Pyodide under Node, exactly as the browser upload does,
// and compare its output with a command-line reference CSV byte for byte.
//
//   node app/scripts/check_scorer_parity.mjs <reference.csv> [input.csv]
//
// <reference.csv>: env_pipeline.py --compact output for the same input, e.g. a moon_pipeline run's
// environment.csv. [input.csv] defaults to the published sample input.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

const data = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "data");
const [reference, input = join(data, "environment", "sample_input.csv")] = process.argv.slice(2);
if (!reference) {
  console.error("Usage: node app/scripts/check_scorer_parity.mjs <reference.csv> [input.csv]");
  process.exit(2);
}

const environment = JSON.parse(readFileSync(join(data, "environment.json"), "utf8"));
const pyodide = await loadPyodide();
await pyodide.loadPackage("pyyaml");
pyodide.FS.mkdirTree("/scorer");
for (const file of environment.upload_files) {
  const bytes = readFileSync(join(data, file.file));
  if (createHash("sha256").update(bytes).digest("hex") !== file.sha256) throw new Error(`${file.name}: hash mismatch`);
  pyodide.FS.writeFile(`/scorer/${file.name}`, bytes);
}
pyodide.runPython("import sys\nsys.path.insert(0, '/scorer')");
pyodide.globals.set("upload_text", readFileSync(input, "utf8").replace(/^﻿/, ""));
const result = JSON.parse(pyodide.runPython("from score_upload import score\nscore(upload_text, '/scorer')"));
if (!result.ok) {
  console.error(`Scorer error in Pyodide: ${result.error}`);
  process.exit(1);
}
const expected = readFileSync(reference, "utf8");
if (result.csv !== expected) {
  const got = result.csv.split("\n");
  const want = expected.split("\n");
  const line = got.findIndex((text, index) => text !== want[index]);
  console.error(`Mismatch at line ${line + 1}:\n  pyodide: ${got[line]}\n  cli:     ${want[line]}`);
  process.exit(1);
}
console.log(`Pyodide ${pyodide.version}: ${result.scenarios.length} rows identical to ${reference}`);
