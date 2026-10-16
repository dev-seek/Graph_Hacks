import Link from "next/link";
import { TriangleAlert } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

const base =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-5 py-2 font-bold no-underline transition-colors disabled:opacity-60";

export function ButtonLink({
  href,
  tone = "primary",
  children,
  ...rest
}: { href: string; tone?: "primary" | "secondary" | "onNight"; children: ReactNode } & Omit<
  ComponentProps<typeof Link>,
  "href"
>) {
  return (
    <Link href={href} className={`${base} ${tones[tone]}`} {...rest}>
      {children}
    </Link>
  );
}

const tones = {
  primary: "bg-sage text-card hover:bg-[#2c5a4d]",
  secondary: "border-2 border-night bg-card text-night hover:bg-mist",
  onNight: "bg-starlight text-ink hover:bg-[#f5c46a]",
};

export function Button({
  tone = "primary",
  className = "",
  ...rest
}: { tone?: keyof typeof tones } & ComponentProps<"button">) {
  return <button className={`${base} ${tones[tone]} ${className}`} {...rest} />;
}

export function Card({
  children,
  className = "",
  ...rest
}: { children: ReactNode } & ComponentProps<"section">) {
  return (
    <section
      className={`rounded-2xl border border-line bg-card p-5 shadow-sm ${className}`}
      {...rest}
    >
      {children}
    </section>
  );
}

export function Notice({
  tone = "info",
  title,
  live,
  children,
}: {
  tone?: "info" | "urgent";
  title?: string;
  /** Announce to screen readers when it appears (errors, urgent). Static notices stay quiet. */
  live?: boolean;
  children: ReactNode;
}) {
  const cls =
    tone === "urgent"
      ? "border-urgent bg-card text-ink"
      : "border-border bg-card text-ink";
  return (
    <div
      role={tone === "urgent" || live ? "alert" : undefined}
      className={`rounded-xl border-2 p-4 ${cls}`}
    >
      {title ? (
        <p
          className={`flex items-center gap-2 font-bold ${tone === "urgent" ? "text-urgent" : "text-night"}`}
        >
          {tone === "urgent" ? <TriangleAlert aria-hidden="true" size={22} /> : null}
          {title}
        </p>
      ) : null}
      <div>{children}</div>
    </div>
  );
}

export function Loading({ what = "this page" }: { what?: string }) {
  return (
    <p role="status" className="text-muted">
      Loading {what}…
    </p>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Notice tone="info" title="We hit a snag" live>
      <p>{message}</p>
      <div className="mt-3 flex flex-wrap gap-3">
        {onRetry ? (
          <Button tone="secondary" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
        <ButtonLink href="/" tone="secondary">
          Back to the home page
        </ButtonLink>
      </div>
    </Notice>
  );
}
