import { SCHEMA_VERSION } from "./types";
import type {
  AnalogsDocument,
  EarthDocument,
  EnvironmentDocument,
  GridFormat,
  PatchesDocument,
  RegionsDocument,
  TerrainChannel,
} from "./types";

/** A data problem with a message that is safe to show to the user. */
export class DataError extends Error {}

const DATA_ROOT = `${import.meta.env.BASE_URL}data/`;
const cache = new Map<string, Promise<unknown>>();

function cached<T>(key: string, load: () => Promise<T>): Promise<T> {
  let pending = cache.get(key) as Promise<T> | undefined;
  if (!pending) {
    pending = load();
    pending.catch(() => cache.delete(key));
    cache.set(key, pending);
  }
  return pending;
}

async function request(file: string): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(DATA_ROOT + file);
  } catch {
    throw new DataError(`Could not reach the data file ${file}. Check the connection and reload.`);
  }
  // A static dev server answers a missing file with the app's HTML page, so check the type too.
  const type = response.headers.get("content-type") ?? "";
  if (!response.ok || type.includes("text/html")) {
    throw new DataError(`The data file ${file} is missing from this build.`);
  }
  return response;
}

async function loadJson<T extends { schema_version: number }>(file: string): Promise<T> {
  const response = await request(file);
  let document: T;
  try {
    document = (await response.json()) as T;
  } catch {
    throw new DataError(`The data file ${file} is not valid JSON.`);
  }
  if (document.schema_version !== SCHEMA_VERSION) {
    throw new DataError(
      `The data file ${file} uses schema version ${document.schema_version}. This app reads version ${SCHEMA_VERSION}.`,
    );
  }
  return document;
}

export function loadRegions(): Promise<RegionsDocument> {
  return cached("regions.json", () => loadJson<RegionsDocument>("regions.json"));
}

export function loadPatches(file: string): Promise<PatchesDocument> {
  return cached(file, () => loadJson<PatchesDocument>(file));
}

export function loadAnalogs(file: string): Promise<AnalogsDocument> {
  return cached(file, () => loadJson<AnalogsDocument>(file));
}

export async function loadEarth(): Promise<EarthDocument> {
  const { earth_file } = await loadRegions();
  return cached(earth_file, () => loadJson<EarthDocument>(earth_file));
}

export async function loadEnvironment(): Promise<EnvironmentDocument> {
  const { environment_file } = await loadRegions();
  if (!environment_file) throw new DataError("This build has no environment results.");
  return cached(environment_file, () => loadJson<EnvironmentDocument>(environment_file));
}

/** A URL for a file in the data folder, such as the environment sample input. */
export function dataUrl(file: string): string {
  return DATA_ROOT + file;
}

export function loadGridFile(grid: GridFormat): Promise<ArrayBuffer> {
  return cached(grid.file, async () => {
    const buffer = await (await request(grid.file)).arrayBuffer();
    if (buffer.byteLength !== grid.byte_length) {
      throw new DataError(
        `The terrain file ${grid.file} has ${buffer.byteLength} bytes. Its metadata expects ${grid.byte_length}.`,
      );
    }
    return buffer;
  });
}

/** Decode one patch from a region grid file into physical values per channel. */
export function decodePatch(buffer: ArrayBuffer, grid: GridFormat, offset: number): TerrainChannel[] {
  if (grid.dtype !== "int16" || grid.byte_order !== "little") {
    throw new DataError(`Unsupported terrain format: ${grid.dtype}, ${grid.byte_order}-endian.`);
  }
  const [rows, cols] = grid.shape;
  const cells = rows * cols;
  if (grid.bytes_per_patch !== grid.channels.length * cells * 2) {
    throw new DataError("The terrain metadata does not match its grid shape.");
  }
  if (!Number.isInteger(offset) || offset < 0 || offset + grid.bytes_per_patch > buffer.byteLength) {
    throw new DataError("This patch points outside the terrain file.");
  }
  const view = new DataView(buffer, offset, grid.bytes_per_patch);
  return grid.channels.map((channel, index) => {
    const values = new Float32Array(cells);
    for (let cell = 0; cell < cells; cell += 1) {
      values[cell] = view.getInt16((index * cells + cell) * 2, true) / grid.scale;
    }
    return { name: channel.name, unit: channel.unit, rows, cols, values };
  });
}
