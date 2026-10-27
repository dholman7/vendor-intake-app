"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Flags, Status } from "@/components/status";
import { api, shownError } from "@/lib/api";
import { CATEGORY_LABELS, STATUS_LABELS, formatDateTime } from "@/lib/format";
import { VENDOR_STATUSES, type VendorPage } from "@/lib/types";
import { useQuery } from "@/lib/use-query";

const PAGE_SIZE = 10;

function VendorList() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const status = params.get("status") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [search, setSearch] = useState(q);

  function navigate(next: Record<string, string>) {
    const merged = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) merged.set(key, value);
      else merged.delete(key);
    }
    router.replace(`${pathname}?${merged.toString()}`, { scroll: false });
  }

  // Debounce typing into the URL so each keystroke doesn't trigger a request.
  useEffect(() => {
    if (search === q) return;
    const timer = setTimeout(() => navigate({ q: search, page: "" }), 300);
    return () => clearTimeout(timer);
  });

  const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String((page - 1) * PAGE_SIZE) });
  if (q) query.set("q", q);
  if (status) query.set("status", status);
  const key = query.toString();
  const vendors = useQuery(key, () => api<VendorPage>(`/vendors?${key}`));

  const total = vendors.data?.total ?? 0;
  const first = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const last = Math.min(page * PAGE_SIZE, total);

  return (
    <>
      <div className="toolbar" role="search">
        <div className="field">
          <label htmlFor="vendor-search">Search vendors</label>
          <input
            id="vendor-search"
            className="input"
            type="search"
            placeholder="Name contains…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="vendor-status">Status</label>
          <select
            id="vendor-status"
            className="select"
            value={status}
            onChange={(e) => navigate({ status: e.target.value, page: "" })}
          >
            <option value="">All statuses</option>
            {VENDOR_STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {shownError(vendors.error) && (
        <p role="alert" className="alert alert-error">
          {vendors.error?.message}
        </p>
      )}

      <div className="table-wrap" aria-busy={vendors.loading}>
        {vendors.data && vendors.data.items.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th scope="col">Vendor</th>
                <th scope="col">Category</th>
                <th scope="col">Status</th>
                <th scope="col">Needs attention</th>
                <th scope="col">Last updated</th>
              </tr>
            </thead>
            <tbody>
              {vendors.data.items.map((vendor) => (
                <tr key={vendor.id}>
                  <td>
                    <Link href={`/vendors/${vendor.id}`}>{vendor.name}</Link>
                  </td>
                  <td>{CATEGORY_LABELS[vendor.category]}</td>
                  <td>
                    <Status value={vendor.status} />
                  </td>
                  <td>
                    <Flags flags={vendor.flags} />
                  </td>
                  <td>{formatDateTime(vendor.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          !vendors.loading && (
            <div className="empty">
              {q || status ? (
                <p>No vendors match these filters.</p>
              ) : (
                <>
                  <p>No vendors yet. Add one to start collecting their paperwork.</p>
                  <Link href="/vendors/new" className="btn btn-primary">
                    New vendor
                  </Link>
                </>
              )}
            </div>
          )
        )}
      </div>

      {total > 0 && (
        <div className="pager">
          <span>
            Showing {first}–{last} of {total}
          </span>
          <div className="pager-buttons">
            <button
              type="button"
              className="btn"
              disabled={page <= 1}
              onClick={() => navigate({ page: String(page - 1) })}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn"
              disabled={last >= total}
              onClick={() => navigate({ page: String(page + 1) })}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </>
  );
}

export default function VendorsPage() {
  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Vendors</h1>
          <p className="sub">Everyone your team is onboarding, newest first.</p>
        </div>
        <Link href="/vendors/new" className="btn btn-primary">
          New vendor
        </Link>
      </div>
      <Suspense>
        <VendorList />
      </Suspense>
    </main>
  );
}
