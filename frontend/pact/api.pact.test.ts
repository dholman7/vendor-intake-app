/**
 * Consumer contract: what the web app needs from the API, written by exercising lib/client.ts
 * against Pact's mock provider. Responses assert only the fields the UI reads, so the API can
 * add or change anything else without breaking the contract.
 *
 * Auth is a transport concern: the browser sends the session cookie, and provider verification
 * injects one, so no interaction carries credentials. Provider states name the fixtures each
 * interaction needs, with fixed ids the provider creates exactly (backend/tests/contract).
 *
 * Uploads aren't here: the request is multipart with a form field and a file, which Pact's
 * multipart matching (one file part) can't describe. The Playwright suite covers them.
 *
 * npm run test:pact   # writes ../pacts/vendor-intake-web-vendor-intake-api.json
 */
import assert from "node:assert/strict";
import path from "node:path";
import { describe, it } from "node:test";

import { MatchersV3 as M, PactV4 } from "@pact-foundation/pact";

import { ApiError, setApiBase } from "../lib/api";
import * as client from "../lib/client";

const pact = new PactV4({
  consumer: "vendor-intake-web",
  provider: "vendor-intake-api",
  dir: path.resolve(__dirname, "../../pacts"),
  logLevel: "warn",
});

// 32-character ids, as the API issues them. The provider creates rows with exactly these.
const VENDOR = "c0000000000000000000000000000001";
const IN_REVIEW = "c0000000000000000000000000000002";
const READY = "c0000000000000000000000000000003";
const DOCUMENT = "d0000000000000000000000000000001";
const EXTRACTION = "e0000000000000000000000000000001";

// The UI parses times with `new Date(...)`, which reads a time without an offset as local time,
// so the offset is part of what this consumer needs.
const isoTime = M.regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/.source, "2026-11-03T14:00:00Z");
const errorBody = (code: string) => ({ error: { code, message: M.string("Something is wrong") } });

const vendorBody = (id: string, status: string) => ({
  id,
  name: M.string("Acme Freight"),
  category: M.regex("^(software|services|hardware|logistics|other)$", "logistics"),
  contact_email: M.string("ops@acmefreight.example"),
  status,
  flags: M.like([] as string[]),
  submitted_at: status === "draft" ? null : isoTime,
  created_at: isoTime,
  updated_at: isoTime,
});

const extractionBody = {
  id: EXTRACTION,
  kind: "w9",
  status: "pending_review",
  review_note: null,
  fields: { legal_name: { value: M.string("Acme Freight LLC"), confidence: M.decimal(0.95) } },
};

async function rejects(promise: Promise<unknown>, status: number, code: string): Promise<ApiError> {
  const error = await promise.then(
    () => assert.fail("expected the request to fail"),
    (e: unknown) => e,
  );
  assert.ok(error instanceof ApiError);
  assert.equal(error.status, status);
  assert.equal(error.code, code);
  return error;
}

const run = (test: () => Promise<unknown>) => async (server: { url: string }) => {
  setApiBase(server.url);
  await test();
};

describe("session", () => {
  it("signs in with the right password", () =>
    pact
      .addInteraction()
      .given("the demo member exists")
      .uponReceiving("a sign-in with the right password")
      .withRequest("POST", "/api/auth/login", (b) =>
        b.headers({ "content-type": "application/json" }).jsonBody({ email: "member@northwind.test", password: "demo-password" }),
      )
      // The client parses the body as JSON but reads nothing from it: any object will do.
      .willRespondWith(200, (b) => b.jsonBody({}))
      .executeTest(run(() => client.login("member@northwind.test", "demo-password"))));

  it("refuses the wrong password", () =>
    pact
      .addInteraction()
      .given("the demo member exists")
      .uponReceiving("a sign-in with the wrong password")
      .withRequest("POST", "/api/auth/login", (b) =>
        b.headers({ "content-type": "application/json" }).jsonBody({ email: "member@northwind.test", password: "wrong-password" }),
      )
      .willRespondWith(401, (b) => b.jsonBody(errorBody("invalid_credentials")))
      .executeTest(run(() => rejects(client.login("member@northwind.test", "wrong-password"), 401, "invalid_credentials"))));

  it("reads who is signed in", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .uponReceiving("a request for the signed-in user")
      .withRequest("GET", "/api/me")
      .willRespondWith(200, (b) =>
        b.jsonBody({ name: M.string("Morgan Member"), role: "member", tenant: { name: M.string("Northwind Traders") } }),
      )
      .executeTest(
        run(async () => {
          const user = await client.me();
          assert.equal(user.role, "member");
        }),
      ));

  it("signs out", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .uponReceiving("a sign-out")
      .withRequest("POST", "/api/auth/logout")
      .willRespondWith(204)
      .executeTest(run(() => client.logout())));
});

describe("vendors", () => {
  it("lists a page of vendors with the total", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .given("the member has a vendor", { id: VENDOR, status: "draft" })
      .uponReceiving("a request for the first page of vendors")
      .withRequest("GET", "/api/vendors", (b) => b.query({ limit: "20", offset: "0" }))
      .willRespondWith(200, (b) => b.jsonBody({ items: M.eachLike(vendorBody(VENDOR, "draft")), total: M.integer(1) }))
      .executeTest(
        run(async () => {
          const page = await client.listVendors(new URLSearchParams({ limit: "20", offset: "0" }));
          assert.ok(page.total >= page.items.length);
        }),
      ));

  it("creates a vendor", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .uponReceiving("a new vendor")
      .withRequest("POST", "/api/vendors", (b) =>
        b
          .headers({ "content-type": "application/json" })
          .jsonBody({ name: "Contract Freight", category: "logistics", contact_email: "ops@contract.example" }),
      )
      .willRespondWith(201, (b) => b.jsonBody({ id: M.string(VENDOR), status: "draft" }))
      .executeTest(
        run(async () => {
          const vendor = await client.createVendor({ name: "Contract Freight", category: "logistics", contact_email: "ops@contract.example" });
          assert.equal(vendor.status, "draft");
        }),
      ));

  it("reports which field is invalid", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .uponReceiving("a new vendor with an invalid contact email")
      .withRequest("POST", "/api/vendors", (b) =>
        b
          .headers({ "content-type": "application/json" })
          .jsonBody({ name: "Contract Freight", category: "logistics", contact_email: "not-an-email" }),
      )
      .willRespondWith(422, (b) =>
        b.jsonBody({
          error: {
            code: "validation_error",
            message: M.string("Request validation failed"),
            fields: M.eachLike({ field: "contact_email", message: M.string("value is not a valid email address") }),
          },
        }),
      )
      .executeTest(
        run(async () => {
          const error = await rejects(
            client.createVendor({ name: "Contract Freight", category: "logistics", contact_email: "not-an-email" }),
            422,
            "validation_error",
          );
          assert.ok(error.fieldMessage("contact_email"));
        }),
      ));

  it("reads one vendor", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .given("the member has a vendor", { id: VENDOR, status: "draft" })
      .uponReceiving("a request for one vendor")
      .withRequest("GET", `/api/vendors/${VENDOR}`)
      .willRespondWith(200, (b) => b.jsonBody(vendorBody(VENDOR, "draft")))
      .executeTest(run(() => client.getVendor(VENDOR))));

  it("submits a vendor whose documents are all extracted", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .given("the member has a vendor ready to submit", { id: READY })
      .uponReceiving("a submission for review")
      .withRequest("POST", `/api/vendors/${READY}/submit`)
      .willRespondWith(200, (b) => b.jsonBody({ id: READY, status: "in_review" }))
      .executeTest(
        run(async () => {
          const vendor = await client.submitVendor(READY);
          assert.equal(vendor.status, "in_review");
        }),
      ));

  it("refuses to submit a vendor with documents missing", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .given("the member has a vendor", { id: VENDOR, status: "draft" })
      .uponReceiving("a submission with documents missing")
      .withRequest("POST", `/api/vendors/${VENDOR}/submit`)
      .willRespondWith(409, (b) => b.jsonBody(errorBody("documents_incomplete")))
      .executeTest(run(() => rejects(client.submitVendor(VENDOR), 409, "documents_incomplete"))));
});

describe("documents and review", () => {
  const inReview = { vendor: IN_REVIEW, document: DOCUMENT, extraction: EXTRACTION };

  it("lists a vendor's documents", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .given("a vendor is in review with an extracted W-9", inReview)
      .uponReceiving("a request for a vendor's documents")
      .withRequest("GET", `/api/vendors/${IN_REVIEW}/documents`)
      .willRespondWith(200, (b) =>
        b.jsonBody(M.eachLike({ id: DOCUMENT, kind: "w9", filename: M.string("w9.txt"), status: "extracted", created_at: isoTime })),
      )
      .executeTest(run(() => client.vendorDocuments(IN_REVIEW))));

  it("reads a document's extraction", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .given("a vendor is in review with an extracted W-9", inReview)
      .uponReceiving("a request for a document's extraction")
      .withRequest("GET", `/api/documents/${DOCUMENT}/extraction`)
      .willRespondWith(200, (b) => b.jsonBody(extractionBody))
      .executeTest(run(() => client.extraction(DOCUMENT))));

  it("reads a vendor's audit trail", () =>
    pact
      .addInteraction()
      .given("a member is signed in")
      .given("a vendor is in review with an extracted W-9", inReview)
      .uponReceiving("a request for a vendor's audit trail")
      .withRequest("GET", `/api/vendors/${IN_REVIEW}/audit`)
      .willRespondWith(200, (b) =>
        b.jsonBody({
          items: M.eachLike({ id: M.integer(1), action: M.string("vendor.submitted"), at: isoTime, actor: { name: M.string("Morgan Member") } }),
        }),
      )
      .executeTest(run(() => client.vendorAudit(IN_REVIEW))));

  it("shows reviewers the queue", () =>
    pact
      .addInteraction()
      .given("a reviewer is signed in")
      .given("a vendor is in review with an extracted W-9", inReview)
      .uponReceiving("a request for the review queue")
      .withRequest("GET", "/api/review-queue")
      .willRespondWith(200, (b) =>
        b.jsonBody(
          M.eachLike({
            vendor_id: IN_REVIEW,
            vendor_name: M.string("Acme Freight"),
            submitted_at: isoTime,
            lowest_confidence: M.decimal(0.95),
            extractions: M.eachLike(extractionBody),
          }),
        ),
      )
      .executeTest(run(() => client.reviewQueue())));

  it("approves an extraction", () =>
    pact
      .addInteraction()
      .given("a reviewer is signed in")
      .given("a vendor is in review with an extracted W-9", inReview)
      .uponReceiving("an approval")
      .withRequest("POST", `/api/extractions/${EXTRACTION}/decision`, (b) =>
        b.headers({ "content-type": "application/json" }).jsonBody({ decision: "approve" }),
      )
      .willRespondWith(200, (b) => b.jsonBody({ id: EXTRACTION, status: "approved" }))
      .executeTest(run(() => client.decide(EXTRACTION, { decision: "approve" }))));

  it("needs a note to reject", () =>
    pact
      .addInteraction()
      .given("a reviewer is signed in")
      .given("a vendor is in review with an extracted W-9", inReview)
      .uponReceiving("a rejection without a note")
      .withRequest("POST", `/api/extractions/${EXTRACTION}/decision`, (b) =>
        b.headers({ "content-type": "application/json" }).jsonBody({ decision: "reject", note: "" }),
      )
      .willRespondWith(422, (b) =>
        b.jsonBody({
          error: {
            code: "validation_error",
            message: M.string("Request validation failed"),
            fields: M.eachLike({ field: "note", message: M.string("A note is required when rejecting") }),
          },
        }),
      )
      .executeTest(
        run(async () => {
          const error = await rejects(client.decide(EXTRACTION, { decision: "reject", note: "" }), 422, "validation_error");
          assert.ok(error.fieldMessage("note"));
        }),
      ));
});
