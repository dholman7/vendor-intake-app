import type { DocumentKind, VendorCategory, VendorStatus } from "./types";

export const KIND_LABELS: Record<DocumentKind, string> = {
  w9: "W-9",
  insurance_certificate: "Insurance certificate",
  contract: "Contract",
};

export const STATUS_LABELS: Record<VendorStatus, string> = {
  draft: "Draft",
  in_review: "In review",
  approved: "Approved",
  rejected: "Changes requested",
};

export const CATEGORY_LABELS: Record<VendorCategory, string> = {
  software: "Software",
  services: "Services",
  hardware: "Hardware",
  logistics: "Logistics",
  other: "Other",
};

export const FIELD_LABELS: Record<string, string> = {
  legal_name: "Legal name",
  tax_id_last4: "Tax ID (last 4)",
  business_type: "Business type",
  insurer: "Insurer",
  policy_number: "Policy number",
  coverage_amount: "Coverage",
  expiry_date: "Expires",
  counterparty: "Counterparty",
  effective_date: "Effective",
};

export const FLAG_LABELS: Record<string, string> = {
  insurance_expiring_soon: "Insurance expires within 30 days",
  insurance_expired: "Insurance expired",
};

const AUDIT_LABELS: Record<string, string> = {
  "vendor.created": "Created the vendor",
  "vendor.updated": "Updated vendor details",
  "vendor.submitted": "Submitted for review",
  "vendor.approved": "Vendor approved",
  "vendor.rejected": "Requested changes",
  "document.uploaded": "Uploaded a document",
  "document.extracted": "Fields extracted",
  "document.failed": "Extraction failed",
  "extraction.approved": "Approved extracted fields",
  "extraction.rejected": "Rejected extracted fields",
};

export function auditLabel(action: string): string {
  return AUDIT_LABELS[action] ?? action;
}

const dateTime = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" });
const dateOnly = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeZone: "UTC" });
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : "—";
}

/** Renders an extracted field value; dates and money get human formatting. */
export function formatFieldValue(name: string, value: string | null): string {
  if (value === null) return "Not found";
  if (name.endsWith("_date")) return dateOnly.format(new Date(`${value}T00:00:00Z`));
  if (name === "coverage_amount") return usd.format(Number(value));
  if (name === "tax_id_last4") return `•••••${value}`;
  return value;
}
