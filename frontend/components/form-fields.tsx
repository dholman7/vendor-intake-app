import { FIELD_LABELS, formatFieldValue } from "@/lib/format";
import type { ExtractedField } from "@/lib/types";

function band(confidence: number): "" | "mid" | "low" {
  if (confidence < 0.5) return "low";
  return confidence < 0.8 ? "mid" : "";
}

/** Extracted values laid out like the boxes on a paper form, with confidence along each box's edge. */
export function FormFields({ fields }: { fields: Record<string, ExtractedField> }) {
  return (
    <dl className="form-grid">
      {Object.entries(fields).map(([name, field]) => {
        const percent = Math.round(field.confidence * 100);
        const label = FIELD_LABELS[name] ?? name;
        return (
          <div className="form-box" key={name}>
            <dt className="form-box-label">
              <span>{label}</span>
              <span>{percent}%</span>
            </dt>
            {/* The meter lives inside <dd>: a <dl> group may only hold <dt> and <dd>. */}
            <dd className={`form-box-value${field.value === null ? " missing" : ""}`}>
              {formatFieldValue(name, field.value)}
              <span
                className="confidence"
                role="meter"
                aria-label={`${label} confidence`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percent}
              >
                <span className={`confidence-fill ${band(field.confidence)}`} style={{ width: `${percent}%` }} />
              </span>
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
