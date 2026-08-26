import { useNavigate } from 'react-router-dom'
import BackButton from '../components/BackButton'
import MarketingLayout from '../components/marketing/MarketingLayout'

export default function Terms() {
  const navigate = useNavigate()

  return (
    <MarketingLayout>
    <div className="bg-background px-4 py-8">
      <div className="max-w-sm mx-auto">
        <div className="mb-4">
          <BackButton onClick={() => navigate(-1)} />
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6 space-y-5">
          <div>
            <h1 className="font-heading text-lg font-bold text-primary-900">Terms of Service</h1>
            <p className="text-xs text-primary-400 mt-1">Last updated August 2026</p>
          </div>

          <Section title="Agreement">
            <p>
              GradScout is a small, independently-run project, currently being tested by a closed
              group of people who were personally invited. By using it, you're agreeing to these
              terms. If something here doesn't sit right with you, the straightforward option is
              not to use the app — get in touch instead, this is genuinely still being shaped by
              feedback from people testing it.
            </p>
          </Section>

          <Section title="What GradScout is (and isn't)">
            <p>
              GradScout aggregates and matches graduate job listings published by third-party
              sources — job boards, aggregator APIs, and employer sites. It is not a recruiter,
              employer, or careers advisor, doesn't vet the listings it shows, and doesn't
              guarantee that any listing is accurate, current, or still open. Job details
              (location, salary, description) come from whoever originally posted them, not from
              GradScout — always check the original listing, linked from every job, before
              applying or relying on any detail.
            </p>
          </Section>

          <Section title="Your account">
            <ul className="list-disc pl-5 space-y-1.5">
              <li>Use a real email address you control and keep your password to yourself</li>
              <li>One account per person</li>
              <li>You're responsible for what happens under your account</li>
              <li>You can delete your account at any time from Settings — see the Privacy Notice for what that does</li>
            </ul>
          </Section>

          <Section title="Acceptable use">
            <p>
              Use GradScout the way it's meant to be used — as a person, browsing jobs for
              yourself. Don't try to scrape, bulk-extract, or automate access to the app itself,
              interfere with how it runs, or use it for anything unlawful. Accounts that misuse
              the service may be suspended or removed.
            </p>
          </Section>

          <Section title="Third-party sites and content">
            <p>
              Every job listing links back to the site it came from ("View original"), and
              applying always happens there, not inside GradScout. Those third-party sites have
              their own terms and privacy practices, which GradScout has no control over and isn't
              responsible for. Job listing content — titles, descriptions, employer names — remains
              the property of whoever originally published it.
            </p>
          </Section>

          <Section title="No warranty">
            <p>
              GradScout is provided as-is, with no guarantee that matching, categorisation, or
              deduplication will always be accurate — a job could be miscategorised, a duplicate
              might slip through, or a listing might be shown after it's already closed. It's a
              tool to help your job search, not a substitute for checking the details yourself.
            </p>
          </Section>

          <Section title="Liability">
            <p>
              To the extent the law allows, GradScout isn't liable for any loss or damage arising
              from your use of the app or of any third-party site it links to — including missed,
              incorrect, or outdated job information.
            </p>
          </Section>

          <Section title="Changes">
            <p>
              These terms may be updated as the app develops — meaningful changes will be flagged
              in the app rather than applied silently. Continuing to use GradScout after a change
              means you accept the updated terms.
            </p>
          </Section>

          <Section title="Governing law">
            <p>
              These terms are governed by the law of England and Wales.
            </p>
          </Section>
        </div>
      </div>
    </div>
    </MarketingLayout>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <h2 className="font-heading text-sm font-bold text-primary-900 mb-1.5">{title}</h2>
      <div className="text-sm text-primary-600 leading-relaxed">{children}</div>
    </div>
  )
}
