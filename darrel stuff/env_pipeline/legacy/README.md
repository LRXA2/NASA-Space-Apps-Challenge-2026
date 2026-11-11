# Previous project-integrated implementation

Preserved here with the user's approval on 11 November 2026. This is **not** the active standalone runtime.

- Previous Python scripts, JSON policies, examples, input/evidence files, results and original tests are retained.
- `README_previous.md` is the previous documentation snapshot; historical links/absolute provenance paths may describe the former location.
- `relocation_manifest.json` records former/new paths and original test hashes.
- Only mechanical project-root/helper/source-directory paths were adjusted in the old scripts/source configuration after relocation. The 51 existing test cases are unchanged and still pass.

Run the preserved tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s "darrel stuff/env_pipeline/legacy/tests" -p "test_*.py" -v
```

For current work, use `../env_pipeline.py` and `../config.yml`. The standalone script does not import or read anything in this folder.
