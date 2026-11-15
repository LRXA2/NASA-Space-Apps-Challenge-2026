# Regenerate the app's data (T7)

For whoever updates the website's data after a teammate's model or scorer changes. Gareth does this by default. It takes about 15 minutes, most of it checks.

The website only shows what is committed in `app/public/data/`. Pushing a new export to `main` redeploys the site through [pages.yml](../.github/workflows/pages.yml). Nothing on the website runs the pipelines.

## When to run it

Run it only when one of these changes:

- **A CNN:** Aarron or Hanxi retrains or reruns a model, so the predictions or Earth matches change.
- **The environment scorer:** Darrel changes `env_pipeline.py`, `config.yml` or `sample_input.csv` in `env_algo_task/env_pipeline/`. CI flags this one: `CommittedExportTests` fails until the export is redone.
- **The regions or the export format:** a region is added, or `app/scripts/export_data.py` changes what it writes.

App code or docs changes need no export. The data is frozen for the submission from 2026-11-15, so only run it if a teammate reports a real change.

## Before you start

You need a machine with the git-ignored inputs. CI can't do this, because the inputs are not in the repo.

1. **Python environment.** From the repo root: `uv sync --extra processing --extra model --extra test`. It creates `.venv`.
2. **Node.** Version 22.12 or newer, then `npm --prefix app ci`.
3. **The teammates' runs, in `data/processed/`.** [`data/README.md`](../data/README.md) lists every folder, where it goes and who supplies it. Copy each run folder whole: the code checks each file against its `provenance.json`.
4. **The similarity weights.** Copy `model.pt` as described at the end of the `data/README.md` table.
5. **If a CNN was retrained,** its new run folder has a new name. The model owner updates the run name in `integration/run_all.json` (and `data/README.md`) before you run anything.

The four LOLA maps are not needed. The app uses region-scope environment scores (T4).

## Run it

Windows commands from the repo root. On macOS or Linux use `.venv/bin/python` and forward slashes.

1. **Integrate the three pipelines.** It takes about 90 seconds and writes a new `data/processed/moon_pipeline/<run>/` folder.

   ```powershell
   .\.venv\Scripts\python.exe -m integration.run_all --environment-scope region
   ```

2. **Export for the app.** With no options it reads the newest run and writes all seven regions to `app/public/data/`. Don't add `--region`: that writes a partial catalogue.

   ```powershell
   .\.venv\Scripts\python.exe app\scripts\export_data.py
   ```

   It stops with a message if a record is unsafe to publish. Fix the input, not the check.

3. **Check it.**

   ```powershell
   .\.venv\Scripts\python.exe -m pytest app/scripts/tests
   npm --prefix app run build
   npm --prefix app run check:scorer -- ../data/processed/moon_pipeline/<run>/environment_detailed.csv
   npm --prefix app run check:browser
   ```

   - `check:scorer` runs the website's scorer in Pyodide and must match the Python scorer row for row.
   - `check:browser` needs Chrome. It also checks that each featured patch still fits its kind. If it fails there, pick new patches with the rules in [featured-tiles.md](featured-tiles.md) and update `app/src/featured.json`.
   - If Leibnitz Beta Plateau `r192-c192` no longer shows the same story, update the header demo in `app/src/demo.ts`.

4. **Review the changes.** `git diff --stat app/public/data` should touch only what the teammate changed. A scorer change should not touch `patches/` or `grids/`, and a CNN change should not touch `environment.json`. Spot-check the numbers on a few pages with `npm --prefix app run preview`.

5. **Commit and push to `main`.** Name the pipeline run in the commit message. The Pages workflow redeploys within a few minutes. Open the live site once to check it.

## If something goes wrong

- **`provenance.json` mismatch:** a file in a run folder was edited or re-saved. Copy the folder again from the teammate's zip.
- **A missing run folder:** its name differs from `integration/run_all.json`. Ask the model owner which name is current.
- **`check:scorer` differs:** the scorer changed in a way Pyodide can't run, for example a new package import. Tell Darrel and Gareth before publishing.
