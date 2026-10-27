import type { components } from "./api-schema";

type Schemas = components["schemas"];

export type User = Schemas["UserOut"];
export type Vendor = Schemas["VendorOut"];
export type VendorPage = Schemas["VendorPage"];
export type VendorStatus = Schemas["VendorStatus"];
export type VendorCategory = Schemas["VendorCategory"];
export type VendorDocument = Schemas["DocumentOut"];
export type DocumentKind = Schemas["DocumentKind"];
export type Extraction = Schemas["ExtractionOut"];
export type ExtractedField = Schemas["FieldOut"];
export type ReviewQueueItem = Schemas["ReviewQueueItem"];
export type AuditEvent = Schemas["AuditEventOut"];
export type LoginResponse = Schemas["LoginResponse"];

export const DOCUMENT_KINDS: readonly DocumentKind[] = ["w9", "insurance_certificate", "contract"];
export const VENDOR_STATUSES: readonly VendorStatus[] = ["draft", "in_review", "approved", "rejected"];
export const VENDOR_CATEGORIES: readonly VendorCategory[] = [
  "software",
  "services",
  "hardware",
  "logistics",
  "other",
];
