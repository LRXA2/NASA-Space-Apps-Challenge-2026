# Steps 1–2: source audit and first evidence extraction

**Reviewed: 9 November 2026 (Singapore).** Moon only. No EDA, new recommendation rules, candidate scoring, engine changes or additional downloads were performed. No `dataset_list.csv` or ongoing tracking system was created.

**Status:** Step 1's bounded source/readiness audit is complete. Step 2 has a checked first evidence batch; it is not an exhaustive manual review of every page. Image-only sections and additional requirement tables remain explicitly unresolved.

## Open the evidence

The reusable extraction is in:

[`../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/`](../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/)

| File | Contents |
| --- | --- |
| [mission_equipment_evidence.csv](../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/mission_equipment_evidence.csv) | **26** page-referenced records: equipment configuration, deployment, activities, maintenance, anomalies and historical mission rules. Planned, actual and handbook evidence are distinguished. |
| [eva_percent_remaining.csv](../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/eva_percent_remaining.csv) | **66** oxygen/feedwater/power records from **11 EVA tables** across Apollo 14–17, separated by EVA and CDR/LMP role. These are percentages remaining, not percentages consumed. |
| [apollo17_emu_resources.csv](../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/apollo17_emu_resources.csv) | **18** primary-report resource records across three EVAs/two crew roles: actual/predicted initial, consumed and remaining quantities, reported redlines and durations. Units remain lb or Ah. |
| [apollo17_lm_resource_totals.csv](../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/apollo17_lm_resource_totals.csv) | **Eight** primary-report LM oxygen/water totals with their original phase boundaries. These are not suit stocks or crew metabolic rates. |
| [pdf_source_audit.csv](../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/pdf_source_audit.csv) | Source identities, paths, SHA-256, page counts and text-layer screening for all **11 PDFs**. |
| [extraction_holds.csv](../data/processed/analysis/mission_equipment_extraction/20261108T205148887009Z_evidence/extraction_holds.csv) | Unresolved scans, dense tables, source limitations and missing PDFs. |
| `source_page_contexts.jsonl`, `checked_source_images/` | Exact text contexts and the primary numeric/rule page images checked visually. PDF page numbers are one-based; printed page labels are recorded separately. |
| `source_audit.json`, `verification.json`, `provenance.json` | Frozen acquisition-result summary, extraction checks and input/output hashes. |

These are local generated artifacts under the existing ignored data directory. Keep that directory when using this report; the CSVs are not new inventory trackers.

## Step 1 — What is available

### Environmental/reference inputs

- Project data remains under `darrel stuff/data`; expanded acquisition and the supplied PDFs remain under `D:\projects\NASA Dataset`. Nothing was moved.
- The source register has **53 entries: 38 external/catalog entries, 14 project-input requirements and one baseline**. This does not mean 53 downloaded, applicable datasets.
- Direct presence checks found **144 seasonal Diviner tables and 144 companion XML labels**, **seven SDEM ZIPs**, **six selected LOLA TIFFs** and **ten south-polar illumination TIFFs**. These are presence counts, not a fresh integrity/coverage certification.
- NASA battery and Apollo 15 soil reference folders are present. S02/S03 standards PDFs are present under `moon/eda_pilots/S02` and `S03`; S01 has a curated table extract under `reference/stage3/bvad_rev2`, not the full BVAD PDF.
- D21–D24 remain access-gated in the recorded acquisition evidence. The three missing priority xEMU/dust PDFs remain gaps; none was replaced with an invented value or a different revision.
- The addon downloader now resides inside `download_script/download_script_addons/`. No downloader was modified or executed.

### Addon acquisition snapshot

The exact consumed `results.json` bytes were preserved with the raw extraction. This is a snapshot of recorded **jobs**, not a count of independent observations or proof of a currently running process.

| Dataset | Recorded outcome at the consumed snapshot |
| --- | --- |
| D07 CRaTER | 281 downloaded jobs |
| D08 GOES | 281 downloaded jobs |
| D11 ARTEMIS | 35 downloaded; one verified-existing job |
| D14 Apollo response metadata | One verified-existing job |
| D15 LROC | 11 downloaded jobs |
| D20 Diviner RDR | 80 downloaded; 25 no-observation; 173 error jobs |
| D26 Kaguya | 16 downloaded jobs |
| D27 ShadowCam | 17 downloaded jobs |

The source run may continue changing. These counts do not establish complete three-year/seven-region acquisition. An error is not a no-observation result, and neither is a zero-valued measurement. No large science payload was rehashed for this audit.

### PDF readiness

All **2,903 PDF pages** were screened through their existing text layers. **2,295** yielded at least 80 non-whitespace characters; **608** yielded less. This heuristic locates text/scan limitations, not scientific evidence quality or full manual reading.

- The **221-page LRV integrated handbook** and **176-page press kit** are image-only under this method. Selected LRV cover/configuration/contents images were inspected, but operational pages were not silently treated as extracted.
- The file named `AP7_Prelaunch Mission Operation Report.pdf` identifies **Apollo 17**, not Apollo 7. Prelaunch intentions remain distinct from the separate postflight report.
- `LRV Historical Full Handbook Transcripts.pdf` is a **30-page segment** beginning within the handbook, not evidence that a complete handbook transcript is present.
- Text was captured from the mission requirements, flight rules, LM handbook, mission reports, landmark maps and later EVA assessment. Detailed curation covers the pages identified in the evidence files, not every captured page.

## Step 2 — Evidence now extracted

Examples below describe the sources; **none has been adopted as our algorithm's rule**.

| Topic | Source evidence | Trace |
| --- | --- | --- |
| Activity/return planning | Apollo 17's prelaunch plan ties EVA duration to remaining consumables and operating radius to return capability. | Prelaunch report PDF pp.16–17, printed pp.10–11. |
| Equipment dependencies | The LM10-and-subsequent handbook describes stage-dependent battery supply and EPS-powered atmosphere, oxygen/pressure, water and heat-transport subsystems. | Handbook PDF pp.329, 369, 380; printed pp.2.5-1, 2.6-1, 2.6-16. |
| Deployment/maintenance | Apollo 16 reports rover parking orientation, battery-cover handling and radiator dusting. Apollo 17 describes the fender repair and temperature-indication problems. | Apollo 16 PDF p.97; Apollo 17 PDF pp.139–141. |
| Historical consumable reserve | Apollo 17 final rules specify a 30-minute post-EVA EMU reserve and a seven-hour operational EVA plan. | Final flight rules PDF p.33, printed p.2-8, item 2-27. |
| Conditional communications | The same rules include a five-minute normal-coverage condition with an explicit LCRU/antenna contingency exception. | Final flight rules PDF p.33, item 2-27 G. |
| Equipment thermal management | LRV battery-temperature bounds differ by EVA (125°F on EVAs 1/2; 140°F on EVA 3). The source requires management/traverse adjustments and explicitly says temperature alone does not mean abandoning the rover. | Final flight rules PDF p.50, printed p.3-15, item 3-64. |
| Primary resource budgets | Apollo 17 EMU Table 9-II provides actual/predicted stocks, use, remaining quantities and redlines. LM oxygen/water totals are separately available. | Postflight PDF pp.137–138 and 144–145; printed pp.8-13–14 and 9-6–7. |

### Extraction safeguards and limits

- A normal text PDF and a scanned PDF were sampled before full text extraction. A second sample checked ordinary EVA table rows, the source's `N/A`, and a primary resource table before expanding curation.
- All 18 primary EMU rows were transcribed from the inspected page images and checked for initial-minus-consumed consistency. The LM total tables and two flight-rule pages were also checked visually.
- The later EVA assessment's one missing predicted-power entry stays missing. Its printed differences remain as printed; rounding differences were not silently corrected.
- The LM water table's predicted descent-stage remainder is printed as **48.1 lb**, whereas its displayed tank entries sum to **48.2 lb**. The source total is retained with a limitation note, not repaired without evidence.
- The later EVA assessment and primary Apollo reports are related sources, not independent experimental replications.
- Historical mission rules are configuration- and activity-specific. In particular, equipment battery-temperature limits must not be applied directly to Diviner surface temperature, and Ah must not be treated as Wh.
- No margins, candidate pass/fail results, preference weights or inferred NASA strategies were calculated. Reconciliation of planned duration, actual operation, source discrepancies and transferability belongs to Step 3 and later.

## Remaining extraction work

Step 2 is **partially complete**: the first structured batch is ready for focused EDA, but full extraction is not claimed. Remaining work includes targeted image/OCR review where needed, curation of the mission-requirements tables and selected LM/LRV handbook sections, and visual verification of the dense rover performance table before publishing its numeric columns. Missing PDFs and unsupported modern/polar equipment-response evidence remain explicit holds.

Raw text extraction, page screening and provenance are retained in the sibling `20261108T204505574752Z_full/` directory. The completed evidence batch was checked against **eight recorded input hashes and 15 output hashes**. No existing PDFs or science data were changed.
