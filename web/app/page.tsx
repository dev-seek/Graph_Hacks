export default function Home() {
  return (
    <main className="mx-auto max-w-[65ch] px-4 py-10">
      <section className="on-night rounded-2xl bg-night px-6 py-8 text-card">
        <h1 className="!text-card text-3xl">Constellation</h1>
        <p className="mt-3">
          Tell us your child&apos;s story. We help you gather the right evidence
          and reach the right doctor sooner.
        </p>
        <p className="mt-3 text-starlight">
          This is a placeholder page for the build skeleton.
        </p>
      </section>
      <p className="mt-6 text-muted">
        This doesn&apos;t tell us what&apos;s causing anything. It helps you and
        your doctor decide what to check.
      </p>
      <a
        href="#start"
        className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-sage px-5 font-bold text-card"
      >
        Start
      </a>
    </main>
  );
}
