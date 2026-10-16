import { Clock, HeartHandshake, ShieldCheck } from "lucide-react";
import { TourHost } from "@/components/Tour";
import { ButtonLink } from "@/components/ui";
import { HERO, HOW_IT_WORKS, TRUST_STRIP } from "@/copy";

export default function Home() {
  return (
    <>
      <section className="on-night rounded-2xl bg-night px-6 py-10 text-card">
        <h1 className="max-w-[22ch] text-4xl !text-card sm:text-5xl">{HERO.h1}</h1>
        <p className="mt-4 max-w-[60ch] text-lg">{HERO.sub}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <ButtonLink href="/start" tone="onNight">
            {HERO.primary}
          </ButtonLink>
          <ButtonLink href="/demo" tone="secondary">
            {HERO.secondary}
          </ButtonLink>
        </div>
      </section>

      <section aria-labelledby="how" className="mt-10">
        <h2 id="how" className="text-2xl">
          How it works
        </h2>
        <ol className="mt-4 grid gap-4 sm:grid-cols-3">
          {HOW_IT_WORKS.map((t, i) => (
            <li key={t} className="rounded-2xl border border-line bg-card p-5">
              <span
                aria-hidden="true"
                className="mb-2 flex size-9 items-center justify-center rounded-full bg-night font-bold text-card"
              >
                {i + 1}
              </span>
              {t}
            </li>
          ))}
        </ol>
      </section>

      <section aria-label="Why you can trust it" className="mt-10 rounded-2xl bg-card p-5">
        <p className="flex flex-wrap items-center gap-x-3 gap-y-2 font-bold text-night">
          <ShieldCheck aria-hidden="true" size={20} />
          {TRUST_STRIP}
        </p>
        <ul className="mt-3 grid gap-2 text-muted sm:grid-cols-2">
          <li className="flex gap-2">
            <Clock aria-hidden="true" size={20} className="mt-1 shrink-0" />
            About ten minutes for the first story and a round or two.
          </li>
          <li className="flex gap-2">
            <HeartHandshake aria-hidden="true" size={20} className="mt-1 shrink-0" />
            Made for families of children and teenagers up to age 20.
          </li>
        </ul>
      </section>
      <TourHost role="parent" />
    </>
  );
}
