import { useEffect, useState } from "react";
import { DataError } from "./loaders";

export type Loaded<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

/** Run an async loader when `key` changes. Stale results from an older key are dropped. */
export function useData<T>(key: string, load: () => Promise<T>): Loaded<T> {
  const [state, setState] = useState<{ key: string; value: Loaded<T> }>({ key, value: { status: "loading" } });
  useEffect(() => {
    let current = true;
    load().then(
      (data) => current && setState({ key, value: { status: "ready", data } }),
      (error: unknown) => {
        if (!current) return;
        const message = error instanceof DataError ? error.message : "Something went wrong while reading the data.";
        if (!(error instanceof DataError)) console.error(error);
        setState({ key, value: { status: "error", message } });
      },
    );
    return () => {
      current = false;
    };
    // The loader is tied to `key` by the caller.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state.key === key ? state.value : { status: "loading" };
}
