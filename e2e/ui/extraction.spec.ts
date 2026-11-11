import { expect, test } from "../fixtures";

// Runs against the replay extraction backend (scripts/start-api.sh): an eval-set document gets
// the output Claude gave for it when the extraction evals were recorded, through the app's real
// normalization and grounding. The AI feature is tested end to end, with no API key and no flake.

test.beforeEach(async ({ signIn }) => {
  await signIn("member");
});

test("a value the model misread but grounding caught is shown at zero confidence", async ({ pages, factory }) => {
  // Arrange: in W9-09 the model transposed the tax ID's digits while quoting the document correctly
  const vendor = await factory.vendor();
  await factory.evalDocument(vendor.id, "w9", "W9-09.pdf");

  // Act
  await pages.vendor.goto(vendor.id);

  // Assert: the misread value is flagged for review; the values it read right are not
  await expect(pages.vendor.confidence("Tax ID (last 4)", "w9")).toHaveAttribute("aria-valuenow", "0");
  await expect(pages.vendor.confidence("Legal name", "w9")).toHaveAttribute("aria-valuenow", /^(?:[89]\d|100)$/);
  await expect(pages.vendor.confidence("Business type", "w9")).toHaveAttribute("aria-valuenow", /^(?:[89]\d|100)$/);
});
