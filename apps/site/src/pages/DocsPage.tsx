import { Accordion, AccordionItem } from '@/components/Accordion'

const FAQ = [
  {
    q: 'Where does my data live?',
    a: 'On your laptop, in a SQLite database under your user-data directory plus uploaded PDFs and figures in a sibling folder. Nothing is uploaded to the cloud. Back-up locations are listed in Settings → Storage.',
  },
  {
    q: 'How do I move data to a new laptop?',
    a: 'Use Settings → Export project bundle to create a single .zip with every database row, file and citation. On the new machine, install Research Assistant and choose Import bundle.',
  },
  {
    q: 'Does this work offline?',
    a: 'Yes. The app is fully offline-capable. The only outbound network calls happen when you explicitly use the AI features or fetch a DOI / PubMed record. The mobile PWA caches the last view so highlight-and-read works even on a flaky train wifi.',
  },
  {
    q: 'Can I share a project with a co-author?',
    a: 'Yes — Settings → Sharing invites collaborators by email. Roles (Owner, Editor, Commenter, Viewer) gate every API write. Sharing rides over Tailscale, so co-authors need to be on the same tailnet.',
  },
  {
    q: 'Why do I see "unidentified developer" warnings?',
    a: 'We don’t pay for OS-vendor code-signing certificates ($99/yr for Apple, $300+/yr for Windows EV). The Install page explains the one-time override clicks needed on each platform.',
  },
  {
    q: 'How do I export to DOCX?',
    a: 'From the Manuscript editor toolbar choose Export → DOCX. The exporter produces a Word document with native citation fields, your selected journal template, figures and tables embedded.',
  },
  {
    q: 'Can I import existing references from Zotero / Mendeley / EndNote?',
    a: 'Yes. Export your library from those tools as RIS or BibTeX, then drop the file on Library → Import. Dedup runs automatically across DOI, PMID and title fuzzy-match.',
  },
  {
    q: 'Which statistical tests are supported?',
    a: 'Descriptive stats; t-tests, ANOVA, ANCOVA, non-parametrics, chi-square, Fisher; linear / logistic / Cox regression; mixed-effects; survival; meta-analysis (fixed/random, subgroup, leave-one-out, trim-and-fill); propensity-score matching; CACE / instrumental variables; multiple imputation; power calculations.',
  },
  {
    q: 'Can I use this on iPad / iPhone?',
    a: 'Yes — install the PWA over Tailscale (see the Sync page). It supports reading, highlighting, paragraph-level edits, the stats wizard, checklists and submission mini-apps.',
  },
  {
    q: 'How do I update to a new version?',
    a: 'The desktop app checks GitHub Releases on launch and offers an in-app update via electron-updater. You can also download the latest installer from the Install page at any time.',
  },
  {
    q: 'Is this HIPAA / GDPR compliant?',
    a: 'The app itself is local-first and stores no PHI off your laptop, so compliance depends on your institutional policies. Don’t paste identifiable patient data into AI prompts unless your local AI provider is permitted by your IRB.',
  },
  {
    q: 'How do I report a bug or request a feature?',
    a: 'Open an issue on the GitHub repo (linked in the footer). Include the app version (Help → About), your OS, and the steps to reproduce.',
  },
] as const

export default function DocsPage() {
  return (
    <div className="py-16 sm:py-20">
      <div className="container-narrow">
        <header>
          <span className="badge-soft">Docs</span>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
            Everything you might want to know.
          </h1>
        </header>

        <section id="demo" className="mt-12 grid gap-10 md:grid-cols-2">
          <article>
            <h2 className="text-xl font-semibold tracking-tight">What is this?</h2>
            <p className="mt-3 text-sm leading-relaxed text-ink-muted">
              Research Assistant is a workspace for the whole research lifecycle — library, reader,
              statistics, manuscript editor, peer review, and submission package — in one local-first app.
              Designed primarily for clinical and medical research (RCTs, systematic reviews, observational
              studies, meta-analyses), but the workflow generalises to most quantitative research where you
              need to read papers, run stats, and write up findings.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-ink-muted">
              It runs entirely on your laptop. Your project is a folder you can back up, hand to a co-author,
              or archive when the paper is published. No cloud, no telemetry, no subscriptions.
            </p>
          </article>
          <article>
            <h2 className="text-xl font-semibold tracking-tight">Who is it for?</h2>
            <ul className="mt-3 space-y-2 text-sm leading-relaxed text-ink-muted">
              <li>• Clinical researchers writing original-research and review papers.</li>
              <li>• Fellows and registrars learning statistics and reporting standards.</li>
              <li>• PIs running small teams who want shareable projects without IT overhead.</li>
              <li>• Anyone who prefers their data to live on their own machine.</li>
            </ul>
          </article>
        </section>

        <section className="mt-10 surface-card">
          <h2 className="text-xl font-semibold tracking-tight">What does it cost?</h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-muted">
            Free + open source under MIT. There is no paid tier, no upsell, no analytics. AI features call
            your own configured provider (OpenAI, Anthropic, or a local model) — you pay your provider
            directly, the app never proxies through us.
          </p>
        </section>

        <section className="mt-14">
          <h2 className="text-2xl font-semibold tracking-tight">FAQ</h2>
          <p className="mt-2 text-sm text-ink-muted">Tap any question to expand.</p>
          <div className="mt-6" data-testid="faq-accordion">
            <Accordion>
              {FAQ.map((item) => (
                <AccordionItem key={item.q} question={item.q}>
                  {item.a}
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </section>
      </div>
    </div>
  )
}
