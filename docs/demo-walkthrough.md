# Local app demonstration

Verified on 2026-11-15 against `8769b86` and local interaction fixes. No public host is configured.
The committed exports contain seven regions, 2,910 tiles, and 43,650 Earth matches.

Build the app with `npm --prefix app ci` and `npm --prefix app run build`.
For an interactive review, run `npm --prefix app run preview`, then stop it with Ctrl+C when finished.
The browser check in the [app README](../app/README.md#verify-a-local-build) opens no listening port.

## Main walkthrough

Use the four header links: Region → Patch → Earth analogs → Best match.
They follow Gareth's current example in `app/src/demo.ts`:

1. Open Leibnitz Beta Plateau, patch `r192-c192`.
2. Its highest shape-similarity result is Wadi Rum: cosine 0.9687, but zero of five physical checks in band.
3. Compare rank 5, Atacama: cosine 0.9518, with four of five checks in band.
4. Open the pair comparison. Show the check bands and optional table. Use arrow keys on a grid to move all four cursors.
5. Explain that cosine measures learned shape similarity. It is not a percentage or a suitability rating.

The automated browser check reopens all four header destinations from the production files.
The team has not selected the final featured list for each region (T6).

## Additional verified examples

These use each tile's rank 1 match. They remain alternatives to the header walkthrough.

| Region | Patch | Earth match | Cosine | Physical checks in band |
| --- | --- | --- | --- | --- |
| Haworth | `r544-c544` | Atacama | 0.9981 | 5 of 5 |
| Malapert Massif | `r128-c384` | Wadi Rum | 0.9824 | 0 of 5 |
| de Gerlache–Kocher Massif | `r224-c288` | Death Valley | 0.9947 | 4 of 5 |

Open `#/region/<region>/patch/<patch>/analogs`, then select rank 1.
Use region slugs `haworth`, `malapert-massif`, and `de-gerlache-kocher-massif`.
The longer [featured-tile draft](featured-tiles.md) still needs team selection.

## Environment and upload

1. Open `#/environment/eda_007`. Operations fails the Earth-visibility gate and has no final score. Survival remains separate.
2. Open `#/environment/eda_008`. It has environment results and no terrain coverage.
3. On `#/environment`, show the six Apollo references separately. Their inputs are best-effort estimates, not measured site assessments.
4. Open `#/upload` and expand "Where the input values come from" for source and preparation guidance. Download the unchanged template, edit unique row IDs, and retain column names.
5. Upload a CSV. Row buttons open and focus their domain details without leaving the upload page. A second upload reuses Pyodide.

The browser check uses `eda_001`, `eda_007`, and `dummy_003` from the template to exercise Pass, Fail, and Unknown.
The dummy row is a test fixture. It is excluded from the published site catalogue.
All 83 template rows match the current Python scorer in the Pyodide parity check.

## Limits and handoff

- Environment inputs are mostly assumptions. Potential sites need better measurements before suitability can be assessed.
- Scores are region-wide in this export. They do not distinguish patches within a region.
- CNN classes are model predictions from Earth-trained models. They do not certify lunar safety.
- Earth simulation readiness is uncomputed. Terrain uploads and browser CNN inference are not implemented.
- A real screen-reader pass, final feature acceptance, export ownership, and hosted verification remain open.
- `scripts/prepare_demo` defaults to Haworth only and needs ignored research bundles. Use the Node build for the full committed catalogue.

Current decisions and teammate answers are in [team-blockers.md](team-blockers.md).
