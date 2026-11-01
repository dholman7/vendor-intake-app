import { expect, expectStatus, test } from "../../fixtures";

test("A member cannot approve an extraction", { tag: "@KAN-1" }, async ({ apiAs, factory }) => {
  // Arrange: a vendor in review with an extraction awaiting a decision
  const member = await apiAs("member");
  const { vendor, documents, extractions } = await factory.vendorInReview();

  // Act: the member attempts to approve the extraction
  const response = await member.post(`/api/extractions/${extractions.w9.id}/decision`, {
    data: { decision: "approve" },
  });

  // Assert
  const body = await expectStatus(response, 403);
  expect(body.error.code).toBe("forbidden");
  expect((await factory.extraction(documents.w9.id)).status).toBe("pending_review");
  const after = await expectStatus(await member.get(`/api/vendors/${vendor.id}`), 200);
  expect(after.status).toBe("in_review");
});
