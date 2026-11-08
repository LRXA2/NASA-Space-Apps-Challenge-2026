# Environmental Dataset Register

## Required Stage 3 — controlling priority

The main target is [outline Stage 3](../outline.md#stage-3--environmental-and-equipment-suitability-engine). The older core P1 selection below is **not the complete Stage 3 input list**. Required Stage 3 work comes first, then the original research CSV P1/P2/P3 tags; those tags are not rewritten here.

| Required Stage 3 input / needed analysis | Current data / study | Missing for an operational assessment |
| --- | --- | --- |
| Planetary conditions at selected site/period | D01–D06/D19/D20; Dar_029/030 plus existing thermal/terrain/geometry EDA. | Requested period and applicable dated terrain-aware conditions; PCP is phase context, not mission-time extremes. |
| Mission duration/activities | M04/M07 field contract and Dar_029/031 readiness/sensitivity. | Actual mission schedule; sensitivity axes are not mission inputs. |
| Crew requirements and consumables | New S01 BVAD Rev2 curated reference rates; S02 NASA-STD-3001 V2 F PDF; Dar_031. | Selected crew, adopted requirements/rates, stocks, recovery and reserves. |
| Equipment capabilities/limitations | R01/R02/D31 references and Dar_015/016/031; M01/M05/M06/M07/M08 contracts. | Selected hardware and applicable local/test/model response—not generic reference measurements. |
| Safety requirements, adequacy and margins | Dar_029/031, configured Stage 3 models and source-qualified checks. | Complete applicable requirement inventory, limits/provenance and validated evidence. Missing checks stay Unknown. |

[Current audit](EDA/EDA_Results.md#14-golden-stage-3-revamp): all recorded selected files are present at expected size in the audited scope. Four D-sources are gated; D17/D25 are unselected P2 entries; project M-inputs remain missing. This is not a full-archive/all-file checksum claim. S01 full PDF has local HTTP 403; the official-source extract is available. S02 is acquired. [Decisions, EDA and incorporation](purposal.md#3-what-to-recommend).

**Scope:** environmental evidence supporting Moon base-location assessment, with Earth climate/land-cover data kept as analog-training context. Environmental variables are not inputs to the current terrain CNN.

## Stage 3 analysis requirements — from the root outline

[Stage 3](../outline.md#stage-3--environmental-and-equipment-suitability-engine) states input types and assessment processes, not named dataset products. The [proposal](purposal.md#1-literal-stage-3-requirements-and-current-evidence) holds the outline requirements, source-selection decisions and supporting notebook links. The **Stage 3 analysis relevance** column below maps our core selections to those processes; it does not imply the outline explicitly requires these products.

## Status and evidence

Reviewed **7 November 2026** using [executed EDA and accepted runs](EDA/EDA_Results.md) and the [research transfer record](data/manifests/eda_datasets/20261106T154023845509Z/download.json). Acquisition counts retained below describe the documented selections, not complete archives or a new checksum audit of every local file. Transfer completion, EDA completion and a requirement passing are different statuses.

### Priority and progress meanings

- **P1 — Original core selection:** four entries across three dataset families. This is not the full research P1 list.
- **P2 — Conditional support/alternative:** use for a defined question; not an automatic acquisition requirement.
- **P3 — Optional resource study:** requires a specific activity/question and appropriate product selection.
- **Excluded:** Mars is outside the active Earth–Moon work.

Broader research priorities, dataset fields and local analysis scopes are maintained in [Research_Notes.md](research/Research_Notes.md) and [EDA_Notes.md](EDA/EDA_Notes.md#retrievable-dataset-study-scope). This includes radiation, terrain/support and reference experiments beyond the four core entries. Do not silently equate their priorities with this original core selection.

The [single downloader](download_script/download_environmental.py) uses **`darrel stuff/data/`**, creates it if missing, and checks matching downloads before reuse. See the [download instructions](download_script/Download_Dataset_Instructions.md) for selections, limits, retry behaviour and inventories. Data is excluded by [`.gitignore`](.gitignore).

## P1 — Core environmental datasets

| **Priority** | **Purpose** | **Dataset** | **Download URL** | **Progress** | **Evidence** | **Stage 3 analysis relevance** |
| ------------ | ----------- | ----------- | ---------------- | ------------ | ------------ | -------------------------- |
| P1 | Characterize Earth air temperature, precipitation, wind and solar radiation for northern Arizona, Lanzarote and Atacama. | **TerraClimate v1.1**, 2015–2024: `tmin`, `tmax`, `ppt`, `ws`, `srad`; native approximately 4 km grid. | [THREDDS download catalog](https://thredds.northwestknowledge.net/thredds/catalog/TERRACLIMATE_ALL/data/catalog.xml). Regional NetCDF requests are generated by [the downloader](../download%20scripts/download_terraclimate.py). | Recorded acquired: **150 regional year-variable NetCDF subsets**. Local five-site climate EDA executed in **Dar_003**; see accepted runs in the results report. | [Acquisition checklist](../DOWNLOAD_CHECKLIST.md#completed-acquisition); [03 — climate processing](../notebooks/preprocessing/03_earth_climate.ipynb); [25 — native environmental support](../notebooks/exploration/25_environment_native_support_eda.ipynb).  | **Earth analog context, not a direct lunar Stage 3 input.** Climate comparison supports the separate Earth simulation-readiness task. |
| P1 | Extend the same Earth climate coverage to Death Valley and Wadi Rum. | **TerraClimate v1.1 expansion**, same years and five variables; **250 subsets total across all five Earth sites** when combined with the original collection. | [THREDDS download catalog](https://thredds.northwestknowledge.net/thredds/catalog/TERRACLIMATE_ALL/data/catalog.xml); use the same downloader with the expansion boxes and separate output root. | Recorded acquired: **100 additional regional NetCDF subsets**. Expansion included in executed **Dar_003** five-site climate EDA. | [Acquisition checklist](../DOWNLOAD_CHECKLIST.md#completed-acquisition); [26 — environmental expansion](../notebooks/preprocessing/26_earth_environment_expansion.ipynb); [27 — five-site comparison](../notebooks/exploration/27_five_site_environment_eda.ipynb).  | **Earth analog context, not a direct lunar Stage 3 input.** Extend the same comparison to all five Earth sites. |
| P1 | Describe lunar surface temperature and the availability of native thermal observations across the seven lunar regions. | **LRO Diviner south-polar seasonal PCP collection**: phase-bin average bolometric brightness temperatures at nominal 240 m bin resolution; exact footprint geometry is not established by the local EDA. | [NASA PDS seasonal south-polar archive](https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/seasonal/slon/pols/). | Recorded acquired: **144 temperature tables and 144 XML labels**. Used in **Dar_001/002/017/020/024/025**; missing bins and support limits are retained. | [Acquisition checklist](../DOWNLOAD_CHECKLIST.md#completed-acquisition); [06 — Diviner processing](../notebooks/preprocessing/06_diviner_temperature.ipynb); [25 — thermal support and missingness](../notebooks/exploration/25_environment_native_support_eda.ipynb).  | **Site conditions and thermal-control demands.** Analyse location/local-time/phase distributions and coverage. Operating-period extremes and equipment margins still need applicable dated/response inputs. |
| P1 | Describe lunar solar visibility, Earth visibility, permanent shadow and sky visibility. | **2016 lunar polar illumination products / PGDA Product 69**: ten south-polar raster maps; native resolutions differ between products. | [PGDA GeoTIFF directory](https://pgda.gsfc.nasa.gov/data/MoonIllumination/); [NASA PDS original products](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/). | Recorded acquired: **10 south-polar rasters**. Decoded and used in **Dar_002/012/017–020**; mean visibility remains distinct from dated histories. | [Acquisition checklist](../DOWNLOAD_CHECKLIST.md#completed-acquisition); [05 — native lunar environmental crops](../notebooks/preprocessing/05_lunar_terrain_environment.ipynb); [11 — units/readiness checks](../notebooks/preprocessing/11_inspect_environment_and_actions.ipynb); [25 — native environmental support](../notebooks/exploration/25_environment_native_support_eda.ipynb).  | **Site conditions and power/operational context.** Analyse solar/Earth/sky visibility and shadow with terrain. Mean maps alone do not establish power reserves or communications continuity. |

## P2 — Conditional supporting and alternative sources

| **Priority** | **Purpose** | **Dataset** | **Download URL** | **Progress** | **Evidence** |
| ------------ | ----------- | ----------- | ---------------- | ------------ | ------------ |
| P2 | Provide an alternative long-term Earth climate baseline if a specific comparison needs it; not current weather or an automatic replacement for TerraClimate. | **WorldClim 2.1**, historical 1970–2000 monthly climatology. | [WorldClim historical data/download selector](https://www.worldclim.org/data/worldclim21.html). | Mentioned as a baseline/alternative. **No acquisition or processing recorded** in the current checklist; acquire only if needed. | [Outline §2.3](../outline.md#23-earth-environmental-and-accessibility-data); [conditional acquisition policy](../DOWNLOAD_CHECKLIST.md#still-neededbefore-selecting-further-data). |
| P2 | Supply lunar terrain-related uncertainty/effective-resolution context and investigate shadow products where relevant; distinct from Product 69 illumination. | **LOLA / PGDA Product 90**, selected regional context layers. | [PGDA Product 90 catalog](https://pgda.gsfc.nasa.gov/products/90); selections use [the existing downloader](../download%20scripts/download_lola_product90.py). | Selected maps used in **Dar_002/006/013/019/020/023**. The previously excluded slope-error layer is not used in these analyses; audit it before use. Completion of selected maps does not establish full Product 90 coverage. | [Acquisition checklist](../DOWNLOAD_CHECKLIST.md#completed-acquisition); [outline §2.2](../outline.md#22-planetary-environmental-data); [05 — native context crops](../notebooks/preprocessing/05_lunar_terrain_environment.ipynb). |
| P2 | Describe vegetation, water, bare/sparse ground, cropland and built-up classes for environmental/site screening; this is land-cover context, not climate. | **ESA WorldCover 2021 v200**, native 10 m class maps. | [ESA WorldCover data access](https://esa-worldcover.org/en/data-access); selections use [the existing downloader](../download%20scripts/download_worldcover.py). | Original-pipeline records cover all five Earth sites. Land-cover screening is Earth context, not a lunar Stage 3 requirement or proof of current access. | [Acquisition checklist](../DOWNLOAD_CHECKLIST.md#completed-acquisition); [02 — land-cover processing](../notebooks/preprocessing/02_earth_terrain_landcover.ipynb); [22 — screening comparison](../notebooks/exploration/22_cross_region_screening_eda.ipynb); [24 — source checks](../notebooks/exploration/24_candidate_source_check_eda.ipynb). |
| P2 | Supplement built-up-area screening only if existing WorldCover evidence is insufficient. | **Global Human Settlement Layer — GHS-BUILT-S**, built-up surface. | [JRC GHS-BUILT-S download selector](https://human-settlement.emergency.copernicus.eu/download.php?ds=bu). | **Conditional option; no acquisition or processing recorded.** Epoch/resolution and geographic selection remain to be specified if needed. | [Outline §2.3](../outline.md#23-earth-environmental-and-accessibility-data); [conditional acquisition policy](../DOWNLOAD_CHECKLIST.md#still-neededbefore-selecting-further-data). |

## P3 — Optional lunar resource/mineral studies

These are source families, not approved file lists. Resource indicators must not be represented as verified extractable water or site suitability.

| **Priority** | **Purpose** | **Dataset** | **Download URL** | **Progress** | **Evidence** |
| ------------ | ----------- | ----------- | ---------------- | ------------ | ------------ |
| P3 | Investigate lunar hydrogen/neutron evidence if a resource question is added. | **LRO LEND / Lunar Prospector neutron and hydrogen products**. | [Lunar Orbital Data Explorer](https://ode.rsl.wustl.edu/moon2/) — discovery/download interface; select an explicit product and footprint first. | Bounded **D29 LEND** pilot: **6 selected files completed** in the research transfer record. This is not a full LEND/Lunar Prospector archive or an analysed resource assessment. | [Outline §2.2](../outline.md#22-planetary-environmental-data); [conditional acquisition policy](../DOWNLOAD_CHECKLIST.md#still-neededbefore-selecting-further-data). |
| P3 | Investigate lunar mineralogy or spectral resource indicators for a defined analog question. | **Chandrayaan-1 Moon Mineralogy Mapper (M³)** spectral observations. | [Lunar Orbital Data Explorer](https://ode.rsl.wustl.edu/moon2/) — discovery/download interface; select an explicit product and footprint first. | Bounded **D34 M³** pilot: **14 selected files completed** in the research transfer record. Product applicability and resource analysis remain separate work. | [Outline §2.2](../outline.md#22-planetary-environmental-data); [conditional acquisition policy](../DOWNLOAD_CHECKLIST.md#still-neededbefore-selecting-further-data). |

## Excluded — Historical Mars references

Mars sources in the [root outline](../outline.md) are outside this workspace's active Earth–Moon scope and are not pending environmental downloads.

## Where the datasets belong

All paths below are relative to **`darrel stuff/data/`**. Existing root-pipeline paths are not relocated by the downloader.

| Dataset/evidence | Current download location |
| --- | --- |
| Original three-site TerraClimate | `earth/terraclimate/` |
| Death Valley/Wadi Rum TerraClimate | `earth/environment_expansion/20261030/terraclimate/` |
| Diviner seasonal temperature | `moon/diviner/seasonal/` |
| Lunar illumination/visibility | `moon/illumination_2016/` |
| SDEM and selected LOLA support | `moon/sdem/`, `moon/lola_product90/` |
| Bounded research pilots | `moon/eda_pilots/Dxx/<source-hash>/`; some core IDs reuse core paths |
| Battery/soil reference experiments | `reference/battery_tests/`, `reference/apollo15_soil/` |
| Manually supplied D27/D30 | `moon/eda_pilots/D27/manual_M013049982S/` and `moon/eda_pilots/D30/manual_global_cpr_128ppd/`, with labels and receipts. The [relocation journal](data/manifests/file_relocations.json) resolves the original paths in [the manual inventory](data/manifests/eda_datasets/20261107T182412585915Z/inventory.json); local EDA in [Dar_026/027 results](EDA/EDA_Results.md#13-manual-shadowcam-and-mini-rf-incorporation). |
| Processed and EDA exports | `processed/`; accepted stage/run IDs are listed in [EDA results](EDA/EDA_Results.md) |

Keep source labels, receipts and run manifests with their data. A folder or source URL alone does not establish a completed download or valid analysis.

## Where environmental data is discussed

- [Project outline, section 2.2](../outline.md#22-planetary-environmental-data): lunar environmental sources and factors. Historical Mars entries are not active scope.
- [Project outline, section 2.3](../outline.md#23-earth-environmental-and-accessibility-data): Earth environmental sources. The broader source list includes conditional alternatives, not just acquired datasets.
- [Download guide](../download%20scripts/README.md): source selection, download commands, file layouts and verification rules.
- [Notebook 25](../notebooks/exploration/25_environment_native_support_eda.ipynb): native environmental support, lunar thermal missingness and the original three Earth climate regions.
- [Notebook 27](../notebooks/exploration/27_five_site_environment_eda.ipynb): climate comparison across all five Earth development sites. Its OSM analysis is separate logistics context, not part of this environmental register.

## Interpretation limits and remaining environmental work

- **Earth temperature is air temperature; Diviner measures lunar surface brightness temperature.** They are not interchangeable quantities. TerraClimate `tmin`/`tmax` are monthly averages of minimum/maximum temperatures, not daily extremes; `ppt` is a monthly total.
- **Diviner phase-bin averages are not mission-time extremes or a continuous time series.** Preserve missing cells and bins. Requiring complete thermal coverage can exclude entire regions rather than repair missing evidence.
- **Average illumination does not establish continuous-darkness duration.** Earth visibility, solar visibility, permanent shadow and sky visibility remain separate products. Retain documented units and unresolved quality/unit holds.
- **Preserve native spatial and temporal support.** Environmental fields must not be treated as independent 30 m terrain measurements or collapsed into an unsupported suitability score.
- **Remaining Stage 3 work:** supply applicable mission/crew/equipment/safety inputs, validate the required site/period evidence and implement configured checks. Environmental EDA alone cannot establish operating margins or a requirement pass.
