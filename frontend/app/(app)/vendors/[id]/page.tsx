"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useState, type ChangeEvent } from "react";

import { FormFields } from "@/components/form-fields";
import { Flags, Status } from "@/components/status";
import { api, asApiError, shownError } from "@/lib/api";
import { CATEGORY_LABELS, KIND_LABELS, auditLabel, formatDateTime } from "@/lib/format";
import {
  DOCUMENT_KINDS,
  type AuditEvent,
  type DocumentKind,
  type Extraction,
  type Vendor,
  type VendorDocument,
} from "@/lib/types";
import { useQuery } from "@/lib/use-query";

interface Slot {
  document?: VendorDocument;
  extraction?: Extraction;
}

interface VendorBundle {
  vendor: Vendor;
  slots: Record<DocumentKind, Slot>;
  audit: AuditEvent[];
}

async function loadBundle(id: string): Promise<VendorBundle> {
  const [vendor, documents, audit] = await Promise.all([
    api<Vendor>(`/vendors/${id}`),
    api<VendorDocument[]>(`/vendors/${id}/documents`),
    api<{ items: AuditEvent[] }>(`/vendors/${id}/audit`),
  ]);
  // Documents arrive oldest first, so the last one per kind is the current upload.
  const latest = new Map(documents.map((doc) => [doc.kind, doc]));
  const entries = await Promise.all(
    DOCUMENT_KINDS.map(async (kind): Promise<[DocumentKind, Slot]> => {
      const document = latest.get(kind);
      const extraction =
        document?.status === "extracted"
          ? await api<Extraction>(`/documents/${document.id}/extraction`)
          : undefined;
      return [kind, { document, extraction }];
    }),
  );
  return { vendor, slots: Object.fromEntries(entries) as Record<DocumentKind, Slot>, audit: audit.items };
}

function missingKinds(slots: Record<DocumentKind, Slot>): DocumentKind[] {
  return DOCUMENT_KINDS.filter((kind) => {
    const { extraction } = slots[kind];
    return !extraction || extraction.status === "rejected";
  });
}

function DocumentPanel({
  kind,
  slot,
  editable,
  vendorId,
  onUploaded,
}: {
  kind: DocumentKind;
  slot: Slot;
  editable: boolean;
  vendorId: string;
  onUploaded: () => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const { document, extraction } = slot;
  const label = KIND_LABELS[kind];
  const inputId = `upload-${kind}`;

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const body = new FormData();
    body.set("kind", kind);
    body.set("file", file);
    setUploading(true);
    setProblem(null);
    try {
      await api(`/vendors/${vendorId}/documents`, { method: "POST", body });
      onUploaded();
    } catch (err) {
      setProblem(asApiError(err).message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="panel" aria-labelledby={`${kind}-heading`}>
      <div className="panel-head">
        <div>
          <h2 id={`${kind}-heading`}>{label}</h2>
          <p className="panel-meta">
            {document ? `${document.filename}, uploaded ${formatDateTime(document.created_at)}` : "Not uploaded yet"}
          </p>
        </div>
        {extraction ? (
          // Before submission, nobody is reviewing yet; "Awaiting review" would mislead.
          <Status value={extraction.status === "pending_review" && editable ? "extracted" : extraction.status} />
        ) : (
          document && <Status value={document.status} />
        )}
      </div>

      {extraction && <FormFields fields={extraction.fields} />}
      {extraction?.review_note && (
        <p className="alert alert-warn">Reviewer note: {extraction.review_note}</p>
      )}
      {document?.status === "failed" && (
        <p className="alert alert-error">We couldn&apos;t read this file. Upload a text or PDF copy.</p>
      )}
      {problem && (
        <p role="alert" className="alert alert-error">
          {problem}
        </p>
      )}

      {editable && (
        <div className="upload">
          <label htmlFor={inputId} className="btn">
            {uploading ? "Uploading…" : document ? `Replace ${label}` : `Upload ${label}`}
          </label>
          <input
            id={inputId}
            className="visually-hidden"
            type="file"
            accept=".txt,.pdf,.png,.jpg,.jpeg"
            onChange={onFile}
            disabled={uploading}
          />
          <span className="panel-meta">PDF, PNG, JPG, or TXT up to 10 MB</span>
        </div>
      )}
    </section>
  );
}

function VendorDetail() {
  const { id } = useParams<{ id: string }>();
  const bundle = useQuery(`vendor:${id}`, () => loadBundle(id), {
    pollWhile: (data) =>
      Boolean(data && DOCUMENT_KINDS.some((kind) => data.slots[kind].document?.status === "processing")),
  });
  const [submitProblem, setSubmitProblem] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const error = shownError(bundle.error);
  if (error) {
    return (
      <main className="page">
        <p role="alert" className="alert alert-error">
          {error.status === 404 ? "This vendor doesn't exist or belongs to another team." : error.message}
        </p>
        <Link href="/vendors" className="btn">
          Back to vendors
        </Link>
      </main>
    );
  }
  if (!bundle.data) {
    return <main className="page" aria-busy="true" />;
  }

  const { vendor, slots, audit } = bundle.data;
  const editable = vendor.status === "draft" || vendor.status === "rejected";
  const missing = missingKinds(slots);

  async function submit() {
    setSubmitting(true);
    setSubmitProblem(null);
    try {
      await api(`/vendors/${vendor.id}/submit`, { method: "POST" });
      bundle.reload();
    } catch (err) {
      setSubmitProblem(asApiError(err).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <p className="sub">
            <Link href="/vendors">Vendors</Link>
          </p>
          <h1>{vendor.name}</h1>
        </div>
      </div>

      {vendor.status === "rejected" && (
        <p className="alert alert-warn">
          A reviewer requested changes. Replace the flagged documents, then submit again.
        </p>
      )}

      <div className="detail">
        <div className="stack">
          {DOCUMENT_KINDS.map((kind) => (
            <DocumentPanel
              key={kind}
              kind={kind}
              slot={slots[kind]}
              editable={editable}
              vendorId={vendor.id}
              onUploaded={bundle.reload}
            />
          ))}
        </div>

        <aside className="stack">
          <section className="panel" aria-label="Vendor status">
            <div className="panel-head">
              <Status value={vendor.status} />
              <Flags flags={vendor.flags} />
            </div>
            <dl className="facts">
              <dt>Category</dt>
              <dd>{CATEGORY_LABELS[vendor.category]}</dd>
              <dt>Contact</dt>
              <dd>{vendor.contact_email}</dd>
              <dt>Created</dt>
              <dd>{formatDateTime(vendor.created_at)}</dd>
              <dt>Submitted</dt>
              <dd>{formatDateTime(vendor.submitted_at)}</dd>
            </dl>
            {editable && (
              <>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => void submit()}
                  disabled={submitting || missing.length > 0}
                >
                  {submitting ? "Submitting…" : "Submit for review"}
                </button>
                {missing.length > 0 && (
                  <p className="panel-meta">Still needed: {missing.map((k) => KIND_LABELS[k]).join(", ")}</p>
                )}
              </>
            )}
            {submitProblem && (
              <p role="alert" className="alert alert-error">
                {submitProblem}
              </p>
            )}
          </section>

          <section className="panel" aria-labelledby="activity-heading">
            <h2 id="activity-heading">Activity</h2>
            <ol className="timeline">
              {audit.map((event) => (
                <li key={event.id}>
                  {auditLabel(event.action)}
                  <span className="who">{event.actor.name}</span>
                  <time dateTime={event.at}>{formatDateTime(event.at)}</time>
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>
    </main>
  );
}

export default function VendorDetailPage() {
  return (
    <Suspense fallback={<main className="page" aria-busy="true" />}>
      <VendorDetail />
    </Suspense>
  );
}
