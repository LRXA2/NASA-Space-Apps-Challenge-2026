# Lunar Environmental EDA TODO

Dataset details and progress: [research register](../research/environmental_data.csv). Analysis dimensions: [research README](../research/README.md).

## First: Build on Existing EDA

- [ ] Review notebook 25 and reuse existing processing and summaries.
- [ ] Extend D01 (Diviner polar temperature): compare selected lunar regions and solar-phase bins, showing coverage and missingness.
- [ ] Compare temperature with D02 illumination/shadow and D03 Earth-visibility summaries at compatible spatial scales.
- [ ] Use D06 terrain uncertainty where needed to explain differences between regions.
- [ ] Summarize findings, limitations and useful plots for one coherent regional comparison.

## Next: Explore One New Dataset

- [ ] Choose one question: dated temperature/local solar time (D20), radiation (D07), or temperature versus depth (D21).
- [ ] Read the product documentation and inspect a small data sample with its label.
- [ ] Check fields, units, quality flags, coverage and missing values before expanding the analysis.
- [ ] Complete a focused EDA and explain what it adds to the existing findings.

## Record Progress

- [ ] Save notebooks with useful plots and results retained.
- [ ] Update the research register with actual EDA progress and limitations.

Keep solar-phase averages separate from dated observations. Time-resolved shadows and communications outages require additional modeling and are later work.
