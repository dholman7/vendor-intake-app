import fs from "node:fs";

import { expect, sample, test, uniqueName } from "../../fixtures";

// file, declared type, expected status, content type the server should store (from the extension)
const rows: [string, string, number, string | null][] = [
  ["w9.TXT", "text/plain", 201, "text/plain"],
  ["w9.txt", "application/octet-stream", 201, "text/plain"],
  ["w9.png", "application/pdf", 415, null],
];

for (const [file, declared, status, stored] of rows) {
  test(
    `upload ${file} declared as ${declared} returns ${status}`,
    { tag: "@KAN-3" },
    async ({ apiAs }) => {
      // Arrange: a member and a draft vendor
      const member = await apiAs("member");
      const createRes = await member.post("/api/vendors", {
        data: { name: uniqueName("KAN-3 Vendor"), category: "services", contact_email: "ops@kan3.example" },
      });
      expect(createRes.status(), await createRes.text()).toBe(201);
      const vendor = await createRes.json();

      // Act: upload the sample bytes under the row's filename and declared type
      const uploadRes = await member.post(`/api/vendors/${vendor.id}/documents`, {
        multipart: {
          kind: "w9",
          file: { name: file, mimeType: declared, buffer: fs.readFileSync(sample("w9.txt")) },
        },
      });

      // Assert
      const body = await uploadRes.text();
      expect(uploadRes.status(), body).toBe(status);
      if (status === 415) {
        expect(JSON.parse(body).error.code, body).toBe("unsupported_type");
      }
      if (stored) {
        expect(JSON.parse(body).content_type, body).toBe(stored);
      }
    },
  );
}
