import type { ReactNode } from "react";

type Props = {
  step: number;
  title: string;
  tag?: string;
  children: ReactNode;
  empty?: boolean;
};

export function EvidenceCard({ step, title, tag, children, empty }: Props) {
  return (
    <article className={`evidence-card ${empty ? "is-empty" : ""}`}>
      <div className="evidence-card__node">{String(step).padStart(2, "0")}</div>
      <header>
        <h4>{title}</h4>
        {tag ? <span>{tag}</span> : null}
      </header>
      <div className="evidence-card__body">{children}</div>
    </article>
  );
}
