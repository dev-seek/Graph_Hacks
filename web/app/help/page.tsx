import Link from "next/link";
import { Card } from "@/components/ui";
import { ReopenTour } from "@/components/ReopenTour";

const FAQ: [string, string][] = [
  ["Is this a diagnosis?", "No. Constellation helps you gather information and decide when to see a doctor. It never names a condition for your child."],
  ["What happens to my data?", "We keep your child's age in months and what you tell us. No name, birth date or location. Nothing is sent to anyone unless you choose to share the doctor pack."],
  ["Can I delete everything?", "Yes. Open your journey and choose Delete everything. On this demo site, everything is also deleted after 7 days."],
  ["Why is 'Not sure' always okay?", "Many things are hard to judge at home. 'Not sure' is a real answer and never counts against you. It tells us to ask differently or to leave that check for your doctor."],
  ["What does the doctor get?", "A one-page summary in plain words, with a code. With the code, a clinician can open a clinical view with the findings, their sources and suggested checks."],
  ["What is a doctor pack?", "The one-page summary you print or show on your phone: what you've noticed, checks worth asking about, and questions to ask."],
  ["How many questions will I be asked?", "Three to five at a time. Most families see one to three rounds."],
  ["What if it's an emergency?", "Call your local emergency number now (112 in India and Europe, 911 in the US). Safety checks run on every message you send, before anything else."],
  ["Why didn't it tell me to see a doctor?", "When what you've told us doesn't point to anything that needs a special appointment, we say so and tell you what to keep an eye on. You can still see your doctor whenever you're worried."],
  ["Who is it for?", "Families of children and teenagers from birth to 20 years."],
  ["Does it use AI?", "Yes, for reading your words and wording questions. The decisions and safety rules are ordinary code. The About page has the details."],
  ["Can I come back later?", "Yes. Save the link from your journey page. It keeps checking in as time passes."],
];

export default function Help() {
  return (
    <div className="max-w-[65ch] space-y-6">
      <h1 className="text-3xl">Help</h1>
      <Card aria-labelledby="h-how">
        <h2 id="h-how" className="text-xl">
          How it works, in one minute
        </h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          <li>You tell your child&apos;s story in your own words.</li>
          <li>We check it for anything urgent first, then show you what we understood.</li>
          <li>You answer a few short questions at a time.</li>
          <li>When it&apos;s a good time to see a doctor, you get a one-page summary.</li>
          <li>Doctors can add findings. We keep watching as time passes.</li>
        </ol>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/demo" className="font-bold">
            Watch an example family
          </Link>
          <ReopenTour />
        </div>
        <p className="mt-3">
          <a
            className="inline-block min-h-11 py-2 font-bold underline"
            href="https://github.com/dev-seek/Graph_Hacks/blob/main/docs/USER_GUIDE.md"
            target="_blank"
            rel="noopener noreferrer"
          >
            Read the 5-minute illustrated tour (opens GitHub in a new tab)
          </a>
        </p>
      </Card>
      <section aria-labelledby="h-faq">
        <h2 id="h-faq" className="mb-3 text-xl">
          Common questions
        </h2>
        <div className="space-y-2">
          {FAQ.map(([q, a]) => (
            <details key={q} className="rounded-xl border border-line bg-card px-4">
              <summary className="min-h-11 cursor-pointer py-2 font-bold">{q}</summary>
              <p className="pb-3">{a}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
