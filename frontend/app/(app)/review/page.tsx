"use client";

import Link from "next/link";
import { useState } from "react";

import { FormFields } from "@/components/form-fields";
import { api, asApiError, shownError } from "@/lib/api";
import { KIND_LABELS, formatDateTime } from "@/lib/format";
import type { Extraction, ReviewQueueItem } from "@/lib/types";
import { useQuery } from "@/lib/use-query";

function ExtractionReview({ extraction, onDecided }: { extraction: Extraction; onDecided: () => void }) {
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const label = KIND_LABELS[extraction.kind];
  const noteId = `note-${extraction.id}`;

  async function decide(decision: "approve" | "reject") {
    setBusy(true);
    setProblem(null);
    try {
      await api(`/extractions/${extraction.id}/decision`, {
        method: "POST",
        body: JSON.stringify(decision === "reject" ? { decision, note } : { decision }),
      });
      onDecided();
    } catch (err) {
      const error = asApiError(err);
      setProblem(error.fieldMessage("note") ? "Add a note so the member knows what to fix." : error.message);
      setBusy(false);
    }
  }

  return (
    <section className="stack" aria-label={label}>
      <h3>{label}</h3>
      <FormFields fields={extraction.fields} />
      {problem && (
        <p role="alert" className="alert alert-error">
          {problem}
        </p>
      )}
      {rejecting ? (
        <div className="reject-form">
          <div className="field">
            <label htmlFor={noteId}>What should the member fix?</label>
            <textarea
              id={noteId}
              className="textarea"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="For example: the tax ID doesn't match the W-9 on file."
            />
          </div>
          <div className="decision-row">
            <button type="button" className="btn btn-danger" disabled={busy} onClick={() => void decide("reject")}>
              Send back to member
            </button>
            <button type="button" className="btn btn-quiet" onClick={() => setRejecting(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="decision-row">
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={() => void decide("approve")}
            aria-label={`Approve ${label}`}
          >
            Approve
          </button>
          <button
            type="button"
            className="btn btn-danger"
            disabled={busy}
            onClick={() => setRejecting(true)}
            aria-label={`Request changes to ${label}`}
          >
            Request changes
          </button>
        </div>
      )}
    </section>
  );
}

export default function ReviewQueuePage() {
  const queue = useQuery("review-queue", () => api<ReviewQueueItem[]>("/review-queue"));

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Review queue</h1>
          <p className="sub">Vendors waiting on a decision. Least confident extractions come first.</p>
        </div>
      </div>

      {shownError(queue.error) && (
        <p role="alert" className="alert alert-error">
          {queue.error?.status === 403 ? "Only reviewers and admins can review vendors." : queue.error?.message}
        </p>
      )}

      {queue.data?.length === 0 && (
        <div className="panel empty">
          <p>Nothing to review. Submitted vendors will show up here.</p>
        </div>
      )}

      <div className="queue">
        {queue.data?.map((item) => (
          <article className="panel" key={item.vendor_id} aria-labelledby={`queue-${item.vendor_id}`}>
            <div className="panel-head">
              <div>
                <h2 id={`queue-${item.vendor_id}`}>
                  <Link href={`/vendors/${item.vendor_id}`}>{item.vendor_name}</Link>
                </h2>
                <p className="panel-meta">
                  Submitted {formatDateTime(item.submitted_at)}. Lowest confidence{" "}
                  {Math.round(item.lowest_confidence * 100)}%.
                </p>
              </div>
            </div>
            {item.extractions.map((extraction) => (
              <ExtractionReview key={extraction.id} extraction={extraction} onDecided={queue.reload} />
            ))}
          </article>
        ))}
      </div>
    </main>
  );
}
