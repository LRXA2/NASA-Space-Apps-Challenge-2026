/** "Limits of this page": what this screen cannot tell you. One panel, items marked by a short amber rule. */
export function Limitations({ points }: { points: string[] }) {
  return (
    <section className="limits" aria-labelledby="limits-title">
      <h2 id="limits-title">
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M10 2.5l8 14H2z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
          <path d="M10 8v4M10 14.5v.3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        Limits of this page
      </h2>
      <ul>
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </section>
  );
}
