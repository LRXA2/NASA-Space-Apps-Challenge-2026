> Configuration cleanup: only `config.yml` remains active. The alternative configuration names and commands below are historical and no longer available; older preparation helpers/tests referring to them have not been changed.

> Historical review: the data/results descriptions below refer to the earlier evidence rebuild. The current `inputs/sites.csv` is now the single, mostly populated measurement-level test fixture; invented fills are not source-backed. See README.md for the current workflow. Do not use the older provenance or result files to authenticate the newly filled test values.

# Environmental scoring review and rebuild — 12 November 2026

## Current result

The untrusted old 30-row CSV has been replaced, not repaired or reused. The new
CSV has **7 NASA-region rows, 13 project-proposed footprints and 10 dummy rows**.
The unequal split reflects seven locally supported NASA-region product footprints;
there is no attempt to invent three extra NASA locations to reach ten per group.

Current `outputs/results.csv` uses `config_nasa_reference.yml`. All 20 non-dummy
rows have diagnostic access preferences but **Unknown mandatory gates and no final
rank**. The ten dummy cases exercise boundaries, failures and missing inputs:
five pass both gates, three fail and two are Unknown; only three have complete
preferences and receive final ranks. None of this certifies a habitable base.

## Architecture: what can be inferred from prototype2

Reviewed the reference repository's eligibility engine, scoring policy, feature
composition and pair-scoring orchestration. No source was copied or imported.

| Reference idea | Lunar implementation / decision |
| --- | --- |
| Separate eligibility, features, scoring and recommendations | Keep offline evidence preparation separate from the standalone CSV evaluator. Mandatory checks qualify final recommendations. |
| Policy-controlled factors and multipliers | Reuse the existing YAML configuration and utility functions, not reference personnel thresholds. |
| Explain individual factor effects | Preserve existing utility curves, metric/domain contributions and signed screening distances. |
| Compose distinct scoring systems | Add optional communications geometry through the existing domain loop; old eight-domain configs still work. |
| Priorities and allocation passes | Do not import personnel seniority, course history, scarcity, quotas, caps or CP-SAT allocation. One site's score must not change when unrelated sites are added. |
| Missing-value defaults | Do not transfer zero/default imputation into required physical evidence. Missing remains Unknown. |

Runtime remains **one Python script + chosen YAML + CSV**; only PyYAML is needed
beyond the standard library. No EDA imports, reference-project imports, downloads,
source manifests or preparation metadata files are read by the scorer.

New `role: gate` allows mandatory checks without inventing a soft preference for
the same quantity. `comparison_preference_score` is an **unranked diagnostic**;
it never replaces a withheld final recommendation. Existing final-score keys,
gate-first behavior, curves, contributions and export aliases remain compatible.
Registered metadata is preserved in output. `comparison_group_columns` separates
sample types and footprint scales as well as the existing UTC groups.

## Rule policy: NASA evidence is not a license to invent thresholds

There are two explicit configs:

- `config.yml`: preserves the earlier deliberately unconfigured policy, now with
  communications geometry. All domain weights remain null. No new numerical gate
  is silently adopted in that compatibility/default configuration.
- `config_nasa_reference.yml`: a **dated 2022 access-reference scenario**, not a
  claim about the current Artemis mission plan or a universal long-duration base.
  Only sunlight and Earth-visibility preferences enter its diagnostic aggregate.
  Their equal weights are an explicit **project comparison policy**, not NASA weights.

| Domain | Hard requirement / withheld requirement | Soft preference decision |
| --- | --- | --- |
| Solar illumination | Reference scenario requires **156 h of qualified continuous sunlight within the requested window**: 6.5 days × 24. The actual/proposed rows cannot establish this and remain Unknown. | Higher long-period median solar-disc visibility; fixed physical bounds 0–1, linear utility. Not a generation or storage model. |
| Earth visibility / communications geometry | Qualified minimum available-minus-required RF link margin must be **>=0 dB** in the reference scenario. This is a project performance relation, **not a NASA-published universal link-margin allowance**. No spacecraft, antenna, DSN/relay configuration or working link is invented. | Higher long-period Earth-disc visibility, fixed 0–1 bounds. Partial-disc visibility can overstate DSN contact. |
| Thermal | No adopted candidate-local equipment temperature envelope or component response. Phase summaries, surface maxima and depth-specific annual means cannot be substituted. | No universal “colder is better” or temperature-span weighting adopted. |
| Radiation | No conversion of orbital counters or sky openness to protected local dose; mission duration, transport/shielding and applicable dose budgets are absent. | No counter-to-habitability utility or arbitrary dataset-min/max safety bounds. |
| UV | No local incident/action-weighted exposure and material/protection response. | No duplicate sunlight-derived UV penalty; solar spectra remain nonlocal context. |
| Plasma / charging | Spacecraft potential/density are not regolith potential, discharge risk or hardware tolerance. | No monotonic “lower density is safer” preference. |
| Dust | Detector current and impact-catalog entries are not local deposition, cabin loading or degradation. | No arbitrary dust-current safety score. |
| Seismic | Historical raw waveform counts do not establish polar acceleration demand or recurrence. | No counts-to-structural-safety score. |
| Exosphere | Historical orbital abundance does not establish local compatibility, contamination or breathable atmosphere. | Context only; no “more atmosphere is better” inference. |

These withheld domains remain required topics for any real habitability assessment.
Excluding them from an access-only comparison does **not** declare their hazards
absent or acceptable. `operational_suitability` remains `Not assessed`.

### NASA primary references

- [NASA's 19 August 2022 candidate-region announcement](https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/): the historical 6.5-day sunlight criterion, terrain/lighting/Earth-communications considerations and the declared region names.
- [NASA's 28 October 2024 revised region list](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/): demonstrates that the selection changed. Every NASA row here is labelled **2022**, not misrepresented as a current selected base.
- [NASA LOLA polar illumination product description](https://pgda.gsfc.nasa.gov/products/69): long-period model averages, shorter-period/height/resolution caveats, and partial-Earth-disc limitations for radio studies.

### Cross-checks across EDA, not one notebook

`inputs/source_provenance.json` records exact reviewed run IDs, findings hashes and
native input hashes. In particular:

- **Dar020**: candidate/static/thermal support and cohort distinctions; do not
  copy the previous 21 components into a new “NASA bases” list.
- **Dar021**: normalization and top-set sensitivity; use fixed 0–1 fraction bounds,
  not sample-dependent min/max or empirical correlations as scientific weights.
- **Dar022**: filter before ranking; unresolved operational evidence stays Unknown.
- **Dar054**: all 14 static-versus-regional-point comparison rows explicitly reject
  substituting regional Sun/Earth histories for candidate-local histories. The
  preparation script verifies this contract, rather than filling missing gates.
- **Dar050 + native PRP label in the external dataset folder**: source start/stop
  times are inapplicable; model quantities cannot produce a fabricated chronology.
- **Dar049 and Dar046**: radiation cohort/time sensitivity and spacecraft-plasma
  limitations prevent unqualified local hazard thresholds or monotonic preferences.

These are different support/quantity checks, **not independent measurements of the
same footprint**. Differences across footprint, epoch or statistic are not treated
as contradictions or averaged together to manufacture agreement.

## How the new rows were made

`prepare_sites.py` does not read the previous input or result CSV. It reads native
LOLA solar/Earth visibility and permanent-shadow products at 60 m and sky visibility
at 240 m under `darrel stuff/data/moon/illumination_2016`. It verifies each raster
against its stored SHA-256 receipt, masks fill values **before** applying native
scale/offset, checks physical ranges, and records native support denominators.
Receipt agreement is a local integrity check, not a publisher-checksum claim.

The seven region rectangles come from the existing documented SDEM product extents;
the script independently checks each against the **native elevation TIFF bounds
and CRS**. They are not claimed to be official NASA landing-footprint polygons.

| Group | Construction and meaning |
| --- | --- |
| NASA — 7 | Leibnitz Beta Plateau, Malapert Massif, de Gerlache–Kocher Massif, Haworth, Faustini Rim A, de Gerlache Rim 2 and Connecting Ridge Extension. Each is a NASA-declared **2022 region**, summarized over its locally available SDEM product rectangle. |
| Synthetic — 13 | New hypothetical **1.2 km × 1.2 km** project footprints, using freshly extracted real map-model values rather than fabricated observations. Scan disjoint full-support patches, prefer the larger minimum of Sun/Earth medians, break ties by their equal mean and bounds, then take a regional round-robin. Selection is access-oriented and biased by design—not independent validation or demonstrated buildability. |
| Dummy — 10 | Arbitrary fictional access values, 2030 dates, sunlight durations and RF margins. Includes exact 156 h/0 dB boundaries, small failures, zero/full fractions and missing preferences/gates. No real site identity. |

Sun/Earth/shadow summaries share the same valid native 60 m support. Sky uses its
own documented 240 m support, not resampled pseudo-independent observations.
No modern orbital, historical station or regional-reference value is copied into
a candidate-local hazard field. Unsupported fields remain blank. Static rows carry
no invented requested UTC window. An exact radio budget or continuous sunlight
history must be supplied independently before their gates can pass.

The other folder, `D:/projects/NASA Dataset`, is explicitly reviewed via the native
PRP label and the source-based subject studies, but its nonlocal/model quantities
are **not assigned to local sites merely because files exist**.

## Rebuild and validate

From the repository root (preparation additionally needs numpy and rasterio):

```powershell
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/prepare_sites.py" --sample
# Inspect outputs/verification/sample_check before the full rebuild.
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/prepare_sites.py"
.\.venv\Scripts\python.exe -B "darrel stuff/env_pipeline/env_pipeline.py" --input "darrel stuff/env_pipeline/inputs/sites.csv" --config "darrel stuff/env_pipeline/config_nasa_reference.yml" --output "darrel stuff/env_pipeline/outputs/results.csv" --overwrite
.\.venv\Scripts\python.exe -B -m unittest discover -s "darrel stuff/env_pipeline/tests" -p "test_*.py"
```

Preparation accepts `--external-root` if the second dataset folder moves. Source
products and reviewed EDA artifacts must exist; missing or changed inputs fail
clearly. No download or raw-data rewrite occurs.

Validation: a separate five-row preparation/scoring sample preceded the full run.
**51 targeted tests pass**, including all 44 existing tests unchanged and seven
new tests for legacy config compatibility, gate-only metrics, reference boundaries,
no static-to-continuity/link inference, metadata/groups and the rebuilt fixtures.
The existing uncommitted curves, contribution accounting and independence tests
were retained. Preparation reproducibility and native decoding are also checked
directly, outside the scorer's lightweight runtime test dependencies.

Remaining evidence work: candidate-local dated illumination and radio budgets;
qualified local thermal/radiation/UV/dust/plasma/seismic/exosphere response and
applicable requirements. Without those, a complete operational habitability score
would be unsupported, even though access preferences can be shown numerically.
