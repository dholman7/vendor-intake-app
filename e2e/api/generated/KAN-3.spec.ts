import { readFileSync } from "node:fs";

import { expect, expectStatus, sample, test } from "../../fixtures";

// The server takes a document's content type from its extension, never from the client.
const accepted: [file: string, declared: string][] = [
  ["w9.TXT", "text/plain"],
  ["w9.txt", "application/octet-stream"],
];

for (const [file, declared] of accepted) {
  test(`upload ${file} declared as ${declared} is stored as text/plain`, { tag: "@KAN-3" }, async ({ apiAs, factory }) => {
    // Arrange
    const member = await apiAs("member");
    const vendor = await factory.vendor();

    // Act
    const response = await member.post(`/api/vendors/${vendor.id}/documents`, {
      multipart: { kind: "w9", file: { name: file, mimeType: declared, buffer: readFileSync(sample("w9.txt")) } },
    });

    // Assert
    const document = await expectStatus(response, 201);
    expect(document.content_type).toBe("text/plain");
  });
}

test("upload w9.png declared as application/pdf is refused", { tag: "@KAN-3" }, async ({ apiAs, factory }) => {
  // Arrange
  const member = await apiAs("member");
  const vendor = await factory.vendor();

  // Act
  const response = await member.post(`/api/vendors/${vendor.id}/documents`, {
    multipart: { kind: "w9", file: { name: "w9.png", mimeType: "application/pdf", buffer: readFileSync(sample("w9.txt")) } },
  });

  // Assert
  const body = await expectStatus(response, 415);
  expect(body.error.code).toBe("unsupported_type");
});
