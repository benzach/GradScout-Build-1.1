import { useNavigate } from 'react-router-dom'

export default function Privacy() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="max-w-sm mx-auto">
        <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:text-slate-700 mb-4">
          ← Back
        </button>

        <div className="bg-white rounded-2xl shadow-sm p-6 space-y-5">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">Privacy Notice</h1>
            <p className="text-xs text-slate-400 mt-1">Last updated August 2026</p>
          </div>

          <Section title="Who runs this">
            <p>
              GradScout is a small, independently-run project, currently being tested by a closed
              group of people who were personally invited.{' '}
              <span className="italic text-slate-400">
                [Replace this line with your name and a real contact email before inviting testers.]
              </span>
            </p>
          </Section>

          <Section title="What's collected">
            <ul className="list-disc pl-5 space-y-1.5">
              <li>Your email address and a securely hashed password — hashed with bcrypt, never stored or visible in plain text, not even to whoever runs this app</li>
              <li>The search criteria you save — keywords, locations, industries, salary, contract type</li>
              <li>Which jobs you've seen, applied to, dismissed, or favourited</li>
              <li>If you enable notifications: a technical subscription address tied to your browser or device, used only to deliver them</li>
              <li>Job listings themselves, scraped from public job boards — not personal data about you, just what the matching runs against</li>
            </ul>
          </Section>

          <Section title="Why">
            <p>
              To let you sign in and keep your searches across sessions, and to match and notify
              you about relevant jobs. Nothing here is sold, shared with advertisers, or used for
              anything beyond running this app. There's no ad tracking and no analytics.
            </p>
          </Section>

          <Section title="Who can see it">
            <p>
              Only you, and whoever is running this app during the test — the database is
              self-hosted rather than handed to any third party, but direct access does technically
              exist during this phase. Nobody else can see it.
            </p>
          </Section>

          <Section title="How long it's kept">
            <p>
              For as long as your account exists. You can permanently delete your account, and
              everything tied to it, at any time from the home screen — immediately, with no
              waiting period and no "soft delete".
            </p>
          </Section>

          <Section title="Your rights">
            <p>
              Under UK data protection law, you can ask to see what's stored about you, correct
              it, or delete it. Deletion is self-serve (see above) — for anything else, get in
              touch directly. If a concern is ever left unresolved, you can complain to the UK's
              Information Commissioner's Office at ico.org.uk.
            </p>
          </Section>
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-slate-900 mb-1.5">{title}</h2>
      <div className="text-sm text-slate-600 leading-relaxed">{children}</div>
    </div>
  )
}
