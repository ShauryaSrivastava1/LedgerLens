import Link from "next/link";

export default function NotFound() {
  return (
    <div className="px-8 py-16 max-w-lg">
      <h1 className="font-display text-2xl mb-2">Company not found</h1>
      <p className="text-ink-soft text-sm mb-6">
        There's no company at this address — it may have been removed, or the link is wrong.
      </p>
      <Link href="/" className="rounded bg-ink text-paper px-3 py-1.5 text-sm inline-block hover:bg-ink-soft">
        Back to companies
      </Link>
    </div>
  );
}
