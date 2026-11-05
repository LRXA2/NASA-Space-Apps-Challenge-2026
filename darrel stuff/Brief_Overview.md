# Purpose

This folder contains my (Darrel's) research. My current focus is the environmental aspects of the Moon, with Earth data used for supporting comparisons.

The aim is to understand which conditions matter for people, base operations and exploration, what risks they introduce, and what the available data can actually tell us.

# Objective

Analyse environmental data to understand the conditions, impacts and risks.

- Connect environmental factors to their potential effects and supporting evidence.
- Explore how conditions vary by location, local time or solar phase, where the dataset supports it.
- Record useful findings, missing information and limitations rather than assuming a site is suitable or safe.

# Steps

1. **Research the factors** — understand the environmental conditions and why they matter.
2. **Identify impacts and risks** — consider the effects on people, equipment and operations, with possible workarounds supported by evidence.
3. **Find supporting data** — check the source, available fields, coverage and existing analysis.
4. **Prepare and explore** — verify the downloads, process the required inputs and perform focused EDA.
5. **Record the findings** — explain the observed patterns, uncertainties and next questions.

# Current Stage

Focus on the **P1 datasets** in [Critical_Project_Dataset.md](Critical_Project_Dataset.md). Download and check the required data before starting EDA.

The current scope covers:

- **Lunar temperature:** Diviner data for temperature patterns and coverage across locations and solar-phase bins.
- **Lunar illumination:** solar visibility, Earth visibility, permanent shadow and sky visibility.
- **Earth climate:** temperature, precipitation, wind and solar radiation for supporting comparisons across five Earth sites.

The existing environmental preprocessing and EDA code has been copied into separate Earth and Moon folders. The next work is to prepare the required inputs and run the relevant analyses; copied code alone does not mean the analysis is complete. See the [EDA guide](EDA/README.md#to-be-analysed-moon-data) for the Moon analysis plan and required fields.

# Other Datasets

After the P1 work, refer to [environmental_data.csv](research/environmental_data.csv) for other environmental factors and datasets to explore.

P2 sources are conditional support or alternatives; P3 sources are optional resource studies. Expand when there is a specific question or evidence gap, rather than downloading everything listed. Mars remains outside the active scope.

# Folder Structure

| Folder | Purpose |
| --- | --- |
| **download_script/** | Tools and instructions for acquiring the selected environmental datasets, checking downloads and resuming interrupted transfers. |
| **research/** | Background research, source references, environmental considerations, impacts, risks and evidence gaps. |
| **data/** | Local storage for downloaded datasets, source metadata, download records and generated processing/analysis outputs. |
| **EDA/** | Earth and Moon notebooks for preparing data, exploring patterns and documenting findings and limitations. |

All downloaded data belongs under **`darrel stuff/data/`**. The downloader creates this folder if missing, and its contents are excluded by [`.gitignore`](.gitignore). Keep source labels and download records with the data so findings remain traceable.
