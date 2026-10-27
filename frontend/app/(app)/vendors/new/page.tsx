"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError, api, asApiError } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/format";
import { VENDOR_CATEGORIES, type Vendor, type VendorCategory } from "@/lib/types";

export default function NewVendorPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [category, setCategory] = useState<VendorCategory>("services");
  const [contactEmail, setContactEmail] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const vendor = await api<Vendor>("/vendors", {
        method: "POST",
        body: JSON.stringify({ name, category, contact_email: contactEmail }),
      });
      router.push(`/vendors/${vendor.id}`);
    } catch (err) {
      setError(asApiError(err));
      setBusy(false);
    }
  }

  const nameProblem =
    error?.code === "vendor_name_taken" ? error.message : error?.fieldMessage("name");
  const emailProblem = error?.fieldMessage("contact_email");
  const generalProblem = error && !nameProblem && !emailProblem ? error.message : null;

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>New vendor</h1>
          <p className="sub">You can upload their documents on the next screen.</p>
        </div>
      </div>
      <div className="panel form-card">
        <form onSubmit={onSubmit} noValidate>
          {generalProblem && (
            <p role="alert" className="alert alert-error">
              {generalProblem}
            </p>
          )}
          <div className="field">
            <label htmlFor="vendor-name">Vendor name</label>
            <input
              id="vendor-name"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-invalid={Boolean(nameProblem)}
              aria-describedby={nameProblem ? "vendor-name-problem" : undefined}
              required
            />
            {nameProblem && (
              <p id="vendor-name-problem" className="problem">
                {nameProblem}
              </p>
            )}
          </div>
          <div className="field">
            <label htmlFor="vendor-category">Category</label>
            <select
              id="vendor-category"
              className="select"
              value={category}
              onChange={(e) => setCategory(e.target.value as VendorCategory)}
            >
              {VENDOR_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABELS[c]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="vendor-email">Contact email</label>
            <input
              id="vendor-email"
              className="input"
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              aria-invalid={Boolean(emailProblem)}
              aria-describedby={emailProblem ? "vendor-email-problem" : "vendor-email-hint"}
              required
            />
            {emailProblem ? (
              <p id="vendor-email-problem" className="problem">
                {emailProblem}
              </p>
            ) : (
              <p id="vendor-email-hint" className="hint">
                Where we send onboarding questions.
              </p>
            )}
          </div>
          <div className="actions">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? "Creating…" : "Create vendor"}
            </button>
            <Link href="/vendors" className="btn btn-quiet">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}
