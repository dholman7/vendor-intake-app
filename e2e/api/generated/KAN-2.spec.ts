import fs from "node:fs";

import { expect, sample, test, uniqueName } from "../../fixtures";

test("A second decision on the same extraction is refused", { tag: "@KAN-2" }, async ({ apiAs }) => {
  // Arrange: a member creates a vendor and uploads every required document
  const member = await apiAs("member");
  const reviewer = await apiAs("reviewer");

  const createRes = await member.post("/api/vendors", {
    data: { name: uniqueName("KAN-2 Vendor"), category: "logistics", contact_email: "ops@kan2.example" },
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
  const docs = (await docsRes.json()) as { id: string; kind: string }[];
  const w9 = docs.find((d) => d.kind === "w9");
  expect(w9, await docsRes.text()).toBeTruthy();

  const submitRes = await member.post(`/api/vendors/${vendor.id}/submit`);
  expect(submitRes.status(), await submitRes.text()).toBe(200);

  const extractionRes = await reviewer.get(`/api/documents/${w9!.id}/extraction`);
  expect(extractionRes.status(), await extractionRes.text()).toBe(200);
  const extraction = await extractionRes.json();
  expect(extraction.status, await extractionRes.text()).toBe("pending_review");

  // The reviewer approves the extraction first.
  const approveRes = await reviewer.post(`/api/extractions/${extraction.id}/decision`, {
    data: { decision: "approve" },
  });
  expect(approveRes.status(), await approveRes.text()).toBe(200);

  // Act: the reviewer tries to reject the same extraction
  const rejectRes = await reviewer.post(`/api/extractions/${extraction.id}/decision`, {
    data: { decision: "reject", note: "Changed my mind" },
  });

  // Assert
  const body = await rejectRes.text();
  expect(rejectRes.status(), body).toBe(409);
  expect(JSON.parse(body).error.code, body).toBe("already_decided");

  const afterRes = await reviewer.get(`/api/documents/${w9!.id}/extraction`);
  expect(afterRes.status(), await afterRes.text()).toBe(200);
  const after = await afterRes.json();
  expect(after.status, await afterRes.text()).toBe("approved");
});
