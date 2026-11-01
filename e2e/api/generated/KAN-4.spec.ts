import { expect, expectStatus, test } from "../../fixtures";

test("A whitespace-only note is refused", { tag: "@KAN-4" }, async ({ apiAs, factory }) => {
  // Arrange
  const reviewer = await apiAs("reviewer");
  const { documents, extractions } = await factory.vendorInReview();

  // Act
  const response = await reviewer.post(`/api/extractions/${extractions.w9.id}/decision`, {
    data: { decision: "reject", note: "   " },
  });

  // Assert
  const body = await expectStatus(response, 422);
  expect(body.error.code).toBe("validation_error");
  expect((await factory.extraction(documents.w9.id, "reviewer")).status).toBe("pending_review");
});

test("A rejection note is stored without surrounding spaces", { tag: "@KAN-4" }, async ({ apiAs, factory }) => {
  // Arrange
  const reviewer = await apiAs("reviewer");
  const { documents, extractions } = await factory.vendorInReview();

  // Act
  const response = await reviewer.post(`/api/extractions/${extractions.w9.id}/decision`, {
    data: { decision: "reject", note: "  Tax ID does not match  " },
  });

  // Assert
  const body = await expectStatus(response, 200);
  expect(body.review_note).toBe("Tax ID does not match");
  // Re-read it: the story is about what is stored, not what the decision response echoes.
  expect((await factory.extraction(documents.w9.id, "reviewer")).review_note).toBe("Tax ID does not match");
});
