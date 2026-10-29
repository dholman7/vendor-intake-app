import fs from "node:fs";

import { expect, sample, test, uniqueName } from "../../fixtures";

const rows: [string, string, number][] = [
  ["w9.TXT", "text/plain", 201],
  ["w9.txt", "application/octet-stream", 201],
  ["w9.png", "application/pdf", 415],
];

for (const [file, declared, status] of rows) {
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
    },
  );
}
