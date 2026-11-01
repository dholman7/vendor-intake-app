import { expect, expectStatus, test } from "../../fixtures";

test("A second decision on the same extraction is refused", { tag: "@KAN-2" }, async ({ apiAs, factory }) => {
  // Arrange: a vendor in review whose W-9 extraction the reviewer has already approved
  const reviewer = await apiAs("reviewer");
  const { documents, extractions } = await factory.vendorInReview();
  const decision = `/api/extractions/${extractions.w9.id}/decision`;
  await expectStatus(await reviewer.post(decision, { data: { decision: "approve" } }), 200);

  // Act: the reviewer tries to reject the same extraction
  const response = await reviewer.post(decision, { data: { decision: "reject", note: "Changed my mind" } });

  // Assert
  const body = await expectStatus(response, 409);
  expect(body.error.code).toBe("already_decided");
  expect((await factory.extraction(documents.w9.id, "reviewer")).status).toBe("approved");
});
