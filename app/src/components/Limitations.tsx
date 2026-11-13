/** "Where this breaks down": limits specific to the screen it sits on. */
export function Limitations({ points }: { points: string[] }) {
  return (
    <section className="card limits" aria-labelledby="limits-title">
      <h2 id="limits-title">Where this breaks down</h2>
      <ul>
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </section>
  );
}
