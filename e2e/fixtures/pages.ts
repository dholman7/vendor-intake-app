import { expect, type Locator, type Page } from "@playwright/test";

import { sample, type DocumentKind } from "./factory";

/** The document names the UI shows, per API kind. */
export const KIND_LABELS: Record<DocumentKind, string> = {
  w9: "W-9",
  insurance_certificate: "Insurance certificate",
  contract: "Contract",
};

/** Parts every signed-in screen shares. */
export class AppShell {
  readonly nav: Locator;
  readonly reviewQueueLink: Locator;
  readonly signOutButton: Locator;
  /** The page's main error or notice, not Next.js's route announcer. */
  readonly alert: Locator;

  constructor(readonly page: Page) {
    this.nav = page.getByRole("navigation", { name: "Main", exact: true });
    this.reviewQueueLink = this.nav.getByRole("link", { name: "Review queue", exact: true });
    this.signOutButton = page.getByRole("button", { name: "Sign out", exact: true });
    this.alert = page.getByRole("main").getByRole("alert");
  }

  /** The signed-in person's display name in the header. */
  currentUser(name: string): Locator {
    return this.page.getByText(name);
  }
}

export class SignInPage {
  readonly email: Locator;
  readonly password: Locator;
  readonly submitButton: Locator;
  readonly error: Locator;

  constructor(readonly page: Page) {
    this.email = page.getByLabel("Email");
    this.password = page.getByLabel("Password");
    this.submitButton = page.getByRole("button", { name: "Sign in", exact: true });
    this.error = page.getByRole("main").getByRole("alert");
  }

  async goto() {
    await this.page.goto("/login");
  }

  async signIn(email: string, password: string) {
    await this.email.fill(email);
    await this.password.fill(password);
    await this.submitButton.click();
  }

  /** The demo buttons that fill in a seeded account, e.g. "Fill in member". */
  async fillDemoAccount(name: "member" | "reviewer" | "admin") {
    await this.page.getByRole("button", { name: `Fill in ${name}` }).click();
  }
}

export class VendorListPage {
  readonly heading: Locator;
  readonly search: Locator;
  readonly table: Locator;
  readonly rows: Locator;

  constructor(readonly page: Page) {
    this.heading = page.getByRole("heading", { name: "Vendors", level: 1, exact: true });
    this.search = page.getByLabel("Search vendors");
    this.table = page.getByRole("table");
    this.rows = this.table.getByRole("row");
  }

  async goto() {
    await this.page.goto("/vendors");
  }

  link(name: string): Locator {
    return this.page.getByRole("link", { name });
  }
}

export class NewVendorPage {
  readonly heading: Locator;
  readonly name: Locator;
  readonly category: Locator;
  readonly contactEmail: Locator;
  readonly createButton: Locator;

  constructor(readonly page: Page) {
    this.heading = page.getByRole("heading", { name: "New vendor", exact: true });
    this.name = page.getByLabel("Vendor name");
    this.category = page.getByLabel("Category");
    this.contactEmail = page.getByLabel("Contact email");
    this.createButton = page.getByRole("button", { name: "Create vendor", exact: true });
  }

  async goto() {
    await this.page.goto("/vendors/new");
  }

  async create({ name, email, category }: { name: string; email: string; category?: string }) {
    await this.name.fill(name);
    if (category) await this.category.selectOption(category);
    await this.contactEmail.fill(email);
    await this.createButton.click();
  }
}

export class VendorPage {
  readonly submitButton: Locator;
  readonly approvedNotice: Locator;
  readonly changesRequestedNotice: Locator;

  constructor(readonly page: Page) {
    this.submitButton = page.getByRole("button", { name: "Submit for review", exact: true });
    this.approvedNotice = page.getByText("Vendor approved");
    this.changesRequestedNotice = page.getByText("A reviewer requested changes.");
  }

  async goto(vendorId: string) {
    await this.page.goto(`/vendors/${vendorId}`);
  }

  /** The vendor ID from the current URL, after creating a vendor through the form. */
  idFromUrl(): string {
    const id = new URL(this.page.url()).pathname.split("/").pop();
    if (!id) throw new Error(`not on a vendor page: ${this.page.url()}`);
    return id;
  }

  reviewerNote(note: string): Locator {
    return this.page.getByText(`Reviewer note: ${note}`);
  }

  /** The summary of documents still to upload, e.g. stillNeeded(["w9"]). */
  stillNeeded(kinds: DocumentKind[]): Locator {
    return this.page.getByText(`Still needed: ${kinds.map((k) => KIND_LABELS[k]).join(", ")}`);
  }

  heading(name: string): Locator {
    return this.page.getByRole("heading", { name, level: 1 });
  }

  status(text: string): Locator {
    return this.page.getByLabel("Vendor status").getByText(text);
  }

  /** The extracted fields shown for one document. */
  document(kind: DocumentKind): Locator {
    return this.page.getByRole("region", { name: KIND_LABELS[kind] });
  }

  confidence(fieldLabel: string, kind?: DocumentKind): Locator {
    const scope = kind ? this.document(kind) : this.page;
    return scope.getByRole("meter", { name: `${fieldLabel} confidence` });
  }

  /** Fields extraction couldn't read, within one document. */
  notFound(kind: DocumentKind): Locator {
    return this.document(kind).getByText("Not found");
  }

  async upload(kind: DocumentKind, file = `${kind}.txt`) {
    await this.page.getByLabel(`Upload ${KIND_LABELS[kind]}`).setInputFiles(sample(file));
  }

  /** Extraction runs in the background; the page polls until every document is extracted. */
  async waitUntilReadyToSubmit() {
    await expect(this.submitButton).toBeEnabled({ timeout: 15_000 });
  }
}

export class ReviewQueuePage {
  readonly heading: Locator;

  constructor(readonly page: Page) {
    this.heading = page.getByRole("heading", { name: "Review queue", exact: true });
  }

  async goto() {
    await this.page.goto("/review");
  }

  /** One vendor's card in the queue. */
  card(vendorName: string): Locator {
    return this.page.getByRole("article", { name: vendorName });
  }

  approveButton(vendorName: string, kind: DocumentKind): Locator {
    return this.card(vendorName).getByRole("button", { name: `Approve ${KIND_LABELS[kind]}` });
  }

  async approve(vendorName: string, kind: DocumentKind) {
    await this.approveButton(vendorName, kind).click();
    await expect(this.approveButton(vendorName, kind)).toBeHidden();
  }

  async requestChanges(vendorName: string, kind: DocumentKind, note: string) {
    const card = this.card(vendorName);
    await card.getByRole("button", { name: `Request changes to ${KIND_LABELS[kind]}` }).click();
    await card.getByLabel("What should the member fix?").fill(note);
    await card.getByRole("button", { name: "Send back to member", exact: true }).click();
  }
}

/** Every page object, bound to one browser page. */
export function pagesFor(page: Page) {
  return {
    shell: new AppShell(page),
    signIn: new SignInPage(page),
    vendors: new VendorListPage(page),
    newVendor: new NewVendorPage(page),
    vendor: new VendorPage(page),
    reviewQueue: new ReviewQueuePage(page),
  };
}
export type Pages = ReturnType<typeof pagesFor>;
