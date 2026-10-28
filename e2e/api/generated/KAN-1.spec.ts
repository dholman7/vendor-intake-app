import fs from "node:fs";

import { expect, sample, test, uniqueName } from "../../fixtures";

test("A member cannot approve an extraction", { tag: "@KAN-1" }, async ({ apiAs }) => {
  // Arrange: a member, a vendor in review with extractions awaiting a decision
  const member = await apiAs("member");

  const createRes = await member.post("/api/vendors", {
    data: { name: uniqueName("KAN-1 Vendor"), category: "logistics", contact_email: "ops@kan1.example" },
  });
  expect(createRes.status(), await createRes.text()).toBe(201);
  const vendor = await createRes.json();

  const uploads: [string, string][] = [
    ["w9", "w9.txt"],
    ["insurance_certificate", "insurance_certificate.txt"],
    ["contract", "contract.txt"],
  ];
  for (const [kind, file] of uploads) {
    const uploadRes = await member.post(`/api/vendors/${vendor.id}/documents`, {
      multipart: {
        kind,
        file: { name: file, mimeType: "text/plain", buffer: fs.readFileSync(sample(file)) },
      },
    });
    expect(uploadRes.status(), await uploadRes.text()).toBe(201);
  }

  // Wait for background extraction of every document to finish.
  await expect
    .poll(
      async () => {
        const res = await member.get(`/api/vendors/${vendor.id}/documents`);
        const docs = (await res.json()) as { status: string }[];
        return docs.length === 3 && docs.every((d) => d.status === "extracted");
      },
      { timeout: 30_000 },
    )
    .toBe(true);

  const docsRes = await member.get(`/api/vendors/${vendor.id}/documents`);
  const docs = (await docsRes.json()) as { id: string }[];

  const submitRes = await member.post(`/api/vendors/${vendor.id}/submit`);
  expect(submitRes.status(), await submitRes.text()).toBe(200);

  const extractionRes = await member.get(`/api/documents/${docs[0].id}/extraction`);
  expect(extractionRes.status(), await extractionRes.text()).toBe(200);
  const extraction = await extractionRes.json();
  expect(extraction.status, await extractionRes.text()).toBe("pending_review");

  // Act: the member attempts to approve the extraction
  const decisionRes = await member.post(`/api/extractions/${extraction.id}/decision`, {
    data: { decision: "approve" },
  });

  // Assert
  const body = await decisionRes.text();
  expect(decisionRes.status(), body).toBe(403);
  expect(JSON.parse(body).error.code, body).toBe("forbidden");

  const afterRes = await member.get(`/api/vendors/${vendor.id}`);
  expect(afterRes.status(), await afterRes.text()).toBe(200);
  const after = await afterRes.json();
  expect(after.status, await afterRes.text()).toBe("in_review");
});
