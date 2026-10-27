/** An intake tray holding a filed sheet. */
export function LogoMark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 3.5h8.5L19 7v7" stroke="var(--accent)" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M15.5 3.5V7H19" stroke="var(--accent)" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M7 3.5V14" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M9.5 9.5l1.6 1.6 3.4-3.4" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path
        d="M3 14h5l1.2 2.5h5.6L16 14h5v5.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V14z"
        fill="var(--accent)"
      />
    </svg>
  );
}

export function Logo() {
  return (
    <>
      <LogoMark />
      <span>Vendor Intake</span>
    </>
  );
}
