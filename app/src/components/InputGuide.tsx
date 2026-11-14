// A shortened version of "Where and how to obtain the input values" in env_algo_task/env_pipeline/README.md.
// Keep it in step with that section: the README is the full, authoritative version.

const README =
  "https://github.com/LRXA2/NASA-Space-Apps-Challenge-2026/blob/main/env_algo_task/env_pipeline/README.md#where-and-how-to-obtain-the-input-values";

const LOLA = "https://pgda.gsfc.nasa.gov/products/69";
const SPICE = "https://naif.jpl.nasa.gov/naif/data.html";

interface Row {
  columns: string[];
  source: { label: string; url?: string };
  how: string;
}

const ROWS: Row[] = [
  {
    columns: ["id", "start_utc", "stop_utc"],
    source: { label: "You choose them" },
    how: "Any unique label for id. Give both window times with a time zone, or leave both out. The scorer does not filter data by these dates, so prepare the measurements for that window yourself.",
  },
  {
    columns: ["median_sun_visibility_fraction", "median_earth_visibility_fraction", "median_visible_sky_fraction", "permanently_shadowed_cell_fraction"],
    source: { label: "LOLA polar illumination, Earth-visibility, sky-visibility and permanent-shadow maps", url: LOLA },
    how: "Over the site's map cells: the median Sun and Earth visibility (0–1), the median sky solid angle divided by 4π, and the share of cells in permanent shadow. Give fractions, for example 0.52, not 52.",
  },
  {
    columns: ["window_continuous_sunlight_hours"],
    source: { label: "Your own terrain-horizon model with NAIF/SPICE ephemerides", url: SPICE },
    how: "The longest uninterrupted sunlight in the requested window, in hours. It cannot exceed the window. Leave it blank if you cannot show continuity.",
  },
  {
    columns: ["window_minimum_link_margin_db"],
    source: { label: "A mission RF link budget (antenna, DSN or relay, geometry, losses)" },
    how: "The minimum available-minus-required margin across the window, in dB, outages included. An Earth-visibility map does not give this. Leave blank without a link budget.",
  },
  {
    columns: ["regional_reference_sun_visibility_fraction", "regional_reference_longest_shadow_sample_span_hours"],
    source: { label: "A regional horizon model with NAIF/SPICE kernels", url: SPICE },
    how: "Hourly samples at 2 m height with a 20 km horizon: clear samples ÷ recorded samples, and the longest blocked run in hours.",
  },
  {
    columns: ["lowest_phase_median_temperature_kelvin", "highest_phase_median_temperature_kelvin", "phase_median_temperature_range_kelvin"],
    source: { label: "LRO Diviner derived temperature products", url: "https://pds-geosciences.wustl.edu/missions/lro/diviner.htm" },
    how: "The median for each lunar phase product, then the lowest, the highest and their difference, in kelvin. Leave all three blank if the set of phases is incomplete.",
  },
  {
    columns: ["orbital_radiation_counter_median", "orbital_radiation_counter_maximum"],
    source: { label: "LRO CRaTER secondary science (SEC) tables", url: "https://pds-ppi.igpp.ucla.edu/data/lro-crater/" },
    how: "Daily median and maximum of the GOOD counter, then the median of the daily medians and the maximum of the daily maxima. These are counts, not a radiation dose.",
  },
  {
    columns: ["median_solar_far_uv_irradiance_w_m2"],
    source: { label: "TIMED SEE Level 3 daily spectra", url: "https://lasp.colorado.edu/see/data/daily-averages/level-3/" },
    how: "Integrate each day's spectrum over 115–180 nm, then take the median day, in W/m². This is solar output at 1 AU, not a surface reading.",
  },
  {
    columns: ["median_spacecraft_ion_density_per_cm3", "median_spacecraft_electron_density_per_cm3", "median_spacecraft_electric_potential_volts"],
    source: {
      label: "THEMIS/ARTEMIS ESA L2, probe thb (ARTEMIS P1)",
      url: "https://themis.ssl.berkeley.edu/data_products/index.php?nlist=2&ntype=2_tha-2_thb-2_thc-2_thd-2_the",
    },
    how: "thb_peif_density, thb_peef_density and thb_peif_sc_pot, quality 0 only: daily medians, then the median day. Spacecraft potential is not surface charging.",
  },
  {
    columns: ["historical_median_dust_detector_current_charges_per_second"],
    source: { label: "LADEE LDEX calibrated current tables", url: "https://sbnarchive.psi.edu/pds4/ldex/ladee_ldex_20240411/data_calibrated/" },
    how: "The signed CURRENT values: daily medians, then the median day, in elementary charges per second.",
  },
  {
    columns: ["historical_median_vertical_seismic_rms_counts"],
    source: { label: "Apollo Passive Seismic Experiment, station S12, channel MHZ", url: "https://pds-geosciences.wustl.edu/missions/apollo/apollo_pse.htm" },
    how: "Each day's RMS about the median, √mean((x − median x)²), then the median day, in counts. It is not a ground-motion limit.",
  },
  {
    columns: ["historical_median_orbital_helium_density_per_cm3"],
    source: { label: "LADEE NMS helium abundance tables", url: "https://pds.nasa.gov/ds-view/pds/viewBundle.jsp?identifier=urn:nasa:pds:ladee_nms&version=2.0" },
    how: "He_ABUNDANCE: daily medians, then the median day, in particles per cm³. This is orbital, not surface, atmosphere.",
  },
  {
    columns: ["soil_mean_grain_size_um", "soil_maturity_is_feo", "soil_agglutinates_percent", "soil_feo_wt_percent"],
    source: { label: "Handbook of Lunar Soils (JSC 19069), Apollo sample tables" },
    how: "Mission averages to two decimals: mean grain size in µm, the Is/FeO maturity index, agglutinates in %, and FeO in wt% (15.80, not 0.158). Use site evidence or leave blank.",
  },
];

/** How to fill in the upload template, for readers who have not seen the scorer's README. */
export function InputGuide() {
  return (
    <details className="card input-guide">
      <summary>
        <strong>Where the input values come from</strong>
      </summary>
      <ul>
        <li>Leave a cell blank if you have no supported value. The affected checks then show Unknown, which is not a pass.</li>
        <li>For daily data, take one median per valid day, then the median of those days. Missing days are not zeros.</li>
        <li>Don't mix instruments, versions or modes under one column, and keep notes on your sources, dates and footprint.</li>
      </ul>
      <div className="table-scroll">
        <table className="patch-table input-guide-table">
          <caption>The template's columns, grouped by source.</caption>
          <thead>
            <tr>
              <th scope="col">Columns</th>
              <th scope="col">Source</th>
              <th scope="col">How to get the value</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.columns[0]}>
                <th scope="row">
                  {row.columns.map((column) => (
                    <code key={column}>{column}</code>
                  ))}
                </th>
                <td>{row.source.url ? <a href={row.source.url}>{row.source.label}</a> : row.source.label}</td>
                <td>{row.how}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">
        This is a summary. The full preparation steps, quality filters and caveats are in the{" "}
        <a href={README}>environment scorer's README</a>.
      </p>
    </details>
  );
}
