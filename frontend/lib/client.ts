/**
 * One function per backend endpoint the UI calls, so the requests live in one place. The Pact
 * consumer tests in ../pact exercise these same functions against a mock provider.
 */
import { api } from "./api";
import type {
  AuditEvent,
  DocumentKind,
  Extraction,
  LoginResponse,
  ReviewQueueItem,
  User,
  Vendor,
  VendorCategory,
  VendorDocument,
  VendorPage,
} from "./types";

export interface NewVendor {
  name: string;
  category: VendorCategory;
  contact_email: string;
}

export type Decision = { decision: "approve" } | { decision: "reject"; note: string };

export const me = () => api<User>("/me");

export const login = (email: string, password: string) =>
  api<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });

export const logout = () => api<void>("/auth/logout", { method: "POST" });

export const listVendors = (query: URLSearchParams) => api<VendorPage>(`/vendors?${query}`);

export const createVendor = (vendor: NewVendor) =>
  api<Vendor>("/vendors", { method: "POST", body: JSON.stringify(vendor) });

export const getVendor = (id: string) => api<Vendor>(`/vendors/${id}`);

export const vendorDocuments = (id: string) => api<VendorDocument[]>(`/vendors/${id}/documents`);

export const vendorAudit = (id: string) => api<{ items: AuditEvent[] }>(`/vendors/${id}/audit`);

export const extraction = (documentId: string) => api<Extraction>(`/documents/${documentId}/extraction`);

export function uploadDocument(vendorId: string, kind: DocumentKind, file: Blob, filename: string) {
  const body = new FormData();
  body.set("kind", kind);
  body.set("file", file, filename);
  return api<VendorDocument>(`/vendors/${vendorId}/documents`, { method: "POST", body });
}

export const submitVendor = (id: string) => api<Vendor>(`/vendors/${id}/submit`, { method: "POST" });

export const reviewQueue = () => api<ReviewQueueItem[]>("/review-queue");

export const decide = (extractionId: string, decision: Decision) =>
  api<Extraction>(`/extractions/${extractionId}/decision`, { method: "POST", body: JSON.stringify(decision) });
