/// <reference lib="webworker" />
// Runs Darrel's unmodified environment scorer in Pyodide, off the main thread.
// The Python side (score_upload.py) is shared with app/scripts/check_scorer_parity.mjs.

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";

export interface ScorerFile {
  name: string;
  url: string;
  sha256: string;
}

export interface ScoreRequest {
  id: number;
  files: ScorerFile[];
  csv: string;
}

export type ScoreReply =
  | { id: number; stage: "loading" }
  | { id: number; stage: "done"; result: { ok: true; csv: string; scenarios: unknown[] } | { ok: false; error: string } }
  | { id: number; stage: "failed"; message: string };

interface Pyodide {
  loadPackage(name: string): Promise<void>;
  runPython(code: string): unknown;
  globals: { set(name: string, value: unknown): void };
  FS: { mkdirTree(path: string): void; writeFile(path: string, data: Uint8Array): void };
}

let ready: Promise<Pyodide> | null = null;

async function hex(data: ArrayBuffer): Promise<string> {
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", data));
  return Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function boot(files: ScorerFile[]): Promise<Pyodide> {
  const module = (await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`)) as {
    loadPyodide(options: { indexURL: string }): Promise<Pyodide>;
  };
  const pyodide = await module.loadPyodide({ indexURL: PYODIDE_URL });
  await pyodide.loadPackage("pyyaml");
  pyodide.FS.mkdirTree("/scorer");
  for (const file of files) {
    const response = await fetch(file.url);
    if (!response.ok) throw new Error(`Could not load ${file.name}.`);
    const data = await response.arrayBuffer();
    if ((await hex(data)) !== file.sha256) throw new Error(`${file.name} does not match the published scorer.`);
    pyodide.FS.writeFile(`/scorer/${file.name}`, new Uint8Array(data));
  }
  pyodide.runPython("import sys\nif '/scorer' not in sys.path: sys.path.insert(0, '/scorer')");
  return pyodide;
}

self.onmessage = async (event: MessageEvent<ScoreRequest>) => {
  const { id, files, csv } = event.data;
  const post = (reply: ScoreReply) => (self as unknown as DedicatedWorkerGlobalScope).postMessage(reply);
  try {
    if (!ready) {
      post({ id, stage: "loading" });
      ready = boot(files);
    }
    const pyodide = await ready;
    pyodide.globals.set("upload_text", csv);
    const output = pyodide.runPython("from score_upload import score\nscore(upload_text, '/scorer')") as string;
    post({ id, stage: "done", result: JSON.parse(output) });
  } catch (error) {
    ready = null; // let the next upload retry loading
    post({ id, stage: "failed", message: error instanceof Error ? error.message : String(error) });
  }
};
