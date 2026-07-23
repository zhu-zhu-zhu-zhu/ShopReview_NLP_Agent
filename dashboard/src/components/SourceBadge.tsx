import type { EvidenceSource } from "../agentTypes";

type Props = {
  source: EvidenceSource;
};

export function SourceBadge({ source }: Props) {
  return (
    <div className="source-badge">
      <div>
        <span>API</span>
        <strong className="mono">{source.api}</strong>
      </div>
      <dl>
        <div>
          <dt>batch</dt>
          <dd className="mono">{source.load_batch_id}</dd>
        </div>
        <div>
          <dt>model</dt>
          <dd className="mono">{source.model_version}</dd>
        </div>
        <div>
          <dt>method</dt>
          <dd className="mono">{source.extraction_method}</dd>
        </div>
        {source.generated_at ? (
          <div>
            <dt>generated</dt>
            <dd className="mono">{source.generated_at}</dd>
          </div>
        ) : null}
      </dl>
      <small>{source.source}</small>
    </div>
  );
}
