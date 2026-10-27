import { FLAG_LABELS, STATUS_LABELS } from "@/lib/format";
import type { VendorStatus } from "@/lib/types";

const OTHER_LABELS: Record<string, string> = {
  processing: "Processing",
  extracted: "Extracted",
  failed: "Failed",
  pending_review: "Awaiting review",
  approved: "Approved",
  rejected: "Changes requested",
};

/** Status chip for vendors, documents, and extractions. */
export function Status({ value }: { value: string }) {
  const label = STATUS_LABELS[value as VendorStatus] ?? OTHER_LABELS[value] ?? value;
  return <span className={`status status-${value}`}>{label}</span>;
}

export function Flags({ flags }: { flags: string[] }) {
  if (flags.length === 0) return null;
  return (
    <>
      {flags.map((flag) => (
        <span key={flag} className={`flag flag-${flag}`}>
          {FLAG_LABELS[flag] ?? flag}
        </span>
      ))}
    </>
  );
}
