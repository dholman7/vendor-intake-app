import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, type APIRequestContext } from "@playwright/test";

import { expectStatus } from "./http";
import type { Persona } from "./users";

export const SAMPLES = path.resolve(__dirname, "../../samples");
export const sample = (file: string) => path.join(SAMPLES, file);

/** Vendor names must be unique per tenant, and tests share one database. */
export function uniqueName(prefix: string): string {
  return `${prefix} ${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

export const DOCUMENT_KINDS = ["w9", "insurance_certificate", "contract"] as const;
export type DocumentKind = (typeof DOCUMENT_KINDS)[number];

export interface Vendor {
  id: string;
  name: string;
  status: string;
}
export interface Document {
  id: string;
  kind: DocumentKind;
  status: string;
}
export interface Extraction {
  id: string;
  status: string;
  review_note: string | null;
}

export interface VendorOptions {
  as?: Persona;
  name?: string;
  category?: string;
}
export interface DocumentOptions extends VendorOptions {
  /** Sample file per kind; defaults to `<kind>.txt`, which extracts cleanly. */
  files?: Partial<Record<DocumentKind, string>>;
}

/**
 * Builds test data through the API, asserting every step. Tests arrange state here and spend
 * their own lines only on the behavior under test.
 */
export class Factory {
  constructor(private readonly apiAs: (persona: Persona) => Promise<APIRequestContext>) {}

  async vendor({ as = "member", name, category = "services" }: VendorOptions = {}): Promise<Vendor> {
    const api = await this.apiAs(as);
    const vendorName = name ?? uniqueName("Vendor");
    const response = await api.post("/api/vendors", {
      data: { name: vendorName, category, contact_email: "ops@vendor.example" },
    });
    return expectStatus<Vendor>(response, 201);
  }

  /** Uploads a sample file without waiting for extraction. */
  async upload(vendorId: string, kind: DocumentKind, file = `${kind}.txt`, as: Persona = "member"): Promise<Document> {
    const api = await this.apiAs(as);
    const response = await api.post(`/api/vendors/${vendorId}/documents`, {
      multipart: { kind, file: { name: file, mimeType: "text/plain", buffer: readFileSync(sample(file)) } },
    });
    return expectStatus<Document>(response, 201);
  }

  /** A draft vendor with all three documents uploaded and extracted. */
  async vendorWithDocuments(options: DocumentOptions = {}) {
    const as = options.as ?? "member";
    const vendor = await this.vendor(options);
    for (const kind of DOCUMENT_KINDS) {
      await this.upload(vendor.id, kind, options.files?.[kind], as);
    }
    const api = await this.apiAs(as);
    let documents: Document[] = [];
    await expect
      .poll(
        async () => {
          documents = await expectStatus<Document[]>(await api.get(`/api/vendors/${vendor.id}/documents`), 200);
          return documents.map((d) => d.status).sort();
        },
        { message: "extraction finishes for all three documents", timeout: 30_000 },
      )
      .toEqual(["extracted", "extracted", "extracted"]);
    return { vendor, documents: byKind(documents) };
  }

  /** A vendor submitted for review, with every extraction pending a decision. */
  async vendorInReview(options: DocumentOptions = {}) {
    const as = options.as ?? "member";
    const { vendor, documents } = await this.vendorWithDocuments(options);
    const api = await this.apiAs(as);
    const submitted = await expectStatus<Vendor>(await api.post(`/api/vendors/${vendor.id}/submit`), 200);
    const extractions = {} as Record<DocumentKind, Extraction>;
    for (const kind of DOCUMENT_KINDS) {
      extractions[kind] = await this.extraction(documents[kind].id, as);
      expect(extractions[kind].status, `${kind} extraction awaits review`).toBe("pending_review");
    }
    return { vendor: submitted, documents, extractions };
  }

  async extraction(documentId: string, as: Persona = "member"): Promise<Extraction> {
    const api = await this.apiAs(as);
    return expectStatus<Extraction>(await api.get(`/api/documents/${documentId}/extraction`), 200);
  }
}

function byKind(documents: Document[]): Record<DocumentKind, Document> {
  return Object.fromEntries(documents.map((d) => [d.kind, d])) as Record<DocumentKind, Document>;
}
