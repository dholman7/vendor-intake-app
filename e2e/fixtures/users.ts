export const PASSWORD = "demo-password";
export const USERS = {
  member: "member@northwind.test",
  reviewer: "reviewer@northwind.test",
  admin: "admin@northwind.test",
  otherTenant: "member@globex.test",
} as const;
export type Persona = keyof typeof USERS;
