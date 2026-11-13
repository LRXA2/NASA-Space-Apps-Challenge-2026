import type { ReactNode } from "react";

/** A full-width message for loading, missing data and unknown routes. */
export function PageMessage(props: { title: string; tone?: "info" | "error"; children?: ReactNode }) {
  const tone = props.tone ?? "info";
  return (
    <section className={`message message-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <h1>{props.title}</h1>
      {props.children && <p>{props.children}</p>}
    </section>
  );
}

export function Loading(props: { what: string }) {
  return <PageMessage title={`Loading ${props.what}…`} />;
}
