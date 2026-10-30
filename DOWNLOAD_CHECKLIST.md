# Data acquisition and readiness checklist

Updated **30 October 2026 (Asia/Singapore)** against saved acquisition records and completed processing manifests. **Earth and Moon only; Mars is excluded.** Checked items mean the stated work is complete, not that the data establish analog relevance or mission safety.

## Completed acquisition

- [x] **Seven lunar SDEM regions:** Haworth, Faustini Rim A, deGerlache Rim 2, Connecting Ridge Extension, Leibnitz Beta Plateau, Malapert Massif and deGerlache-Kocher Massif; source terrain and quality layers retained.
- [x] **Selected LOLA Product 90 layers:** regional elevation, slope, uncertainty, effective resolution and measurement counts.
- [x] **Lunar illumination:** 10 south-polar rasters covering solar visibility, Earth visibility, permanent shadow and sky visibility, with download records.
- [x] **Diviner seasonal collection:** 144 temperature tables and 144 XML labels. These are phase-bin average temperatures, not mission-time extremes.
- [x] **Five Earth development sites:** Arizona, Lanzarote, Atacama, Death Valley and Wadi Rum have FABDEM terrain and WorldCover inputs, including the tiles needed for processing context.
- [x] **Climate for all five sites:** TerraClimate v1.1, 2015–2024, `tmin`, `tmax`, `ppt`, `ws`, `srad`; 150 original NetCDF subsets plus 100 for Death Valley/Wadi Rum.
- [x] **Mapped support for all five sites:** six dated Geofabrik extracts—Arizona, Canary Islands, Chile, Bolivia, Northern California and Jordan—with receipts and checksums. Northern California covers the selected Death Valley box.
- [x] **Bounded candidate source checks:** 10 NAIP image subsets, five USGS elevation exports and four Landsat patch observations for nine selected development patches.

See the [environmental expansion acquisition record](notebooks/diagnostics/environment-expansion-research-20261030/ACQUISITION.md), [source-check inventory and findings](notebooks/diagnostics/source-check-20261029T144220349448Z/REPORT.md), and [download instructions](download%20scripts/README.md) for source selections and commands.

## Completed processing and inspection

- [x] Extract and inspect Earth elevation; decode WorldCover; build corrected terrain, class fractions and masks.
- [x] Decode Earth climate packing/missingness and retain its native grid; recompute regional summaries.
- [x] Decode, clip and deduplicate OSM features; retain source dates, tags and quality diagnostics.
- [x] Build separate full-context and image-supported lunar terrain views with explicit quality masks.
- [x] Decode lunar environmental layers; document unit holds and illumination qualifications.
- [x] Process Diviner for all seven regions and inspect per-cell/bin coverage and missingness.
- [x] Complete broad terrain and environmental EDA across the five Earth and seven lunar development regions.

Processing and input records are available in the [notebooks](notebooks/README.md). Read the [EDA summary](EDA_PLAN.md) for key problems: incomplete lunar thermal support, unresolved units/quality, screening sensitivity and unverified operational constraints remain limitations despite completed processing.

## Still needed—before selecting further data

- [ ] Define one mission/training scenario: activity, duration, season, equipment and what Earth must reproduce.
- [ ] Collect documented equipment capabilities and operating limits for that scenario.
- [ ] Define independently assessed analog relevance, including weak/no-match cases.
- [ ] Verify proposed evaluation regions' footprints, shared context and prior exposure; implement a region-role manifest before training. Keep final reserves unopened for EDA.
- [ ] Identify consequential evidence gaps: daily extremes, continuous darkness, thermal-quality concerns, access or other scenario-specific hazards. Acquire additional evidence only where needed; otherwise retain Unknown.

Additional LOLA products, GHSL, alternative climate sources, REMA/ArcticDEM and lunar resource products are **conditional options, not outstanding required downloads**. Proposed reserve acquisitions also require the evaluation checks above; do not bulk-download or inspect them as more development data.

## For each future acquisition

1. Record the question, region, product/version, source dates, license and intended role.
2. Retain URLs, selections, receipts and available publisher checksums; incomplete `.part` files do not count as downloaded.
3. Check integrity and required spatial/temporal coverage, then process in a reproducible notebook and record exact input/output hashes.
4. Update this checklist and the EDA summary when the evidence changes a decision.

This update reconciles existing records; it does not repeat raw-file checksum verification or execute preprocessing.
