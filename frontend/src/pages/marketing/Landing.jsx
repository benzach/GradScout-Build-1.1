import { Link } from 'react-router-dom'
import {
  Bell,
  Filter,
  Mail,
  ShieldCheck,

  Star,
  ArrowRight,
} from 'lucide-react'
import MarketingLayout from '../../components/marketing/MarketingLayout'
import DedupeVisual from '../../components/marketing/DedupeVisual'
import Reveal from '../../components/marketing/Reveal'
import Faq from '../../components/marketing/Faq'

const STEPS = [
  {
    number: '01',
    title: "Tell us what you're after",
    body: "Choose to filter by locations, industries, salary, contract type, or key words. Set up as many saved searches as you like.",
  },
  {
    number: '02',
    title: 'We scan, continuously',
    body: 'GradScout scans across all sources finding you jobs that match your criteria, and notifying you whenever a new listing is found.',
  },
  {
    number: '03',
    title: 'You get one clean feed',
    body: "New matches land ready to favourite, dismiss, or mark as applied; with a push notification or weekly email digest if you'd rather not check manually.",
  },
]

const FEATURES = [
  {
    icon: Filter,
    title: 'Search for exactly what you want',
    body: 'Keywords, exclusions, locations, industries, minimum salary and contract type - combined however you need, across as many saved searches as you want.',
  },
  {
    icon: Bell,
    title: 'Instant push notifications',
    body: "Enable notifications and GradScout will tell you the moment a new match is found.",
  },
  {
    icon: Mail,
    title: "A weekly digest, if you'd prefer",
    body: 'Prefer a roundup to a ping? Turn on the weekly email summary instead - or run both side by side.',
  },
  {
    icon: Star,
    title: "Track what you've seen",
    body: 'Swipe to favourite or dismiss, mark a role as applied, and keep your feed reflecting where you actually are.',
  },
  {
    icon: ShieldCheck,
    title: 'Completely free, always',
    body: "No subscription, no premium tier, no catch - GradScout will never charge for search, matching, or notifications.",
  },
  {
    icon: ShieldCheck,
    title: 'For students, by students',
    body: "GradScout is owned and founded by students; our priority is always to help graduates succeed.",
  },
]

const SOURCES = [
  { name: 'Adzuna', body: 'General graduate & entry-level job search aggregator.' },
  { name: 'Reed', body: "One of the UK's largest job boards." },
  { name: 'Jooble', body: 'International job search engine, active across the UK.' },
]

const FAQ_ITEMS = [
  {
    question: 'Is GradScout free to use?',
    answer:
      "Yes - GradScout is completely free, and always will be. There's no paid tier hiding a better version of the feed.",
  },
  {
    question: 'How is this different from just checking Indeed or LinkedIn myself?',
    answer:
      "Those are just some of the places grad roles get posted. GradScout pulls listings from several job board sources, merges the ones that turn out to be the same underlying role, and matches what's left against your saved criteria - so you check one feed instead of several tabs, without having to work out yourself whether a listing is new or something you've already seen.",
  },
  {
    question: 'Which locations and industries does it cover?',
    answer:
      'The whole of the UK; from the big cities to smaller towns; across industries including law, finance, technology, engineering, consulting, charity & nonprofit, and more. You choose which ones matter when you set up a search.',
  },
  {
    question: 'Do I need to install anything?',
    answer:
      "No - GradScout runs straight in your browser. You can also add it to your phone's home screen for a full-screen, app-like experience, which is what unlocks push notifications.",
  },
  {
    question: "How will I know when something new matches?",
    answer:
      "However suits you: check your feed whenever you like, turn on push notifications for the moment a match appears, or turn on the weekly email digest for a roundup instead. Both can run at once.",
  },
  {
    question: 'What happens to my data?',
    answer:
      'Only what GradScout needs to run your search. See the full Privacy Notice for the exact list of what\'s collected and why. You can permanently delete your account, and everything tied to it, at any time from Settings.',
  },
  {
    question: 'Is GradScout finished?',
    answer:
      "It's a real, working product in active early access. Everything on this page works as described, and it's still being shaped by feedback from the people using it day to day.",
  },
]

export default function Landing() {
  return (
    <MarketingLayout>
      <Hero />
      <HowItWorks />
      <Features />
      <Sources />
      <FaqSection />
      <FinalCta />
    </MarketingLayout>
  )
}

function Hero() {
  return (
    <section className="max-w-6xl mx-auto px-5 sm:px-8 pt-14 pb-20 sm:pt-20 sm:pb-28">
      <div className="grid lg:grid-cols-2 gap-14 lg:gap-10 items-center">
        <Reveal>
          <p className="text-xs font-semibold tracking-wide text-primary-500 bg-secondary-100 inline-block px-3 py-1 rounded-full mb-6">
            Early access · UK graduate &amp; entry-level roles
          </p>
          <h1 className="font-heading text-[2.5rem] leading-[1.05] sm:text-6xl sm:leading-[1.05] font-extrabold text-primary-900 tracking-tight">
            Graduate job hunting can be a challenge. GradScout makes it simple.
          </h1>
          <p className="text-lg text-primary-600 mt-6 leading-relaxed max-w-lg">
            Graduate jobs. Matched to your criteria. All in one place, completely free.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 mt-8">
            <Link
              to="/app/login?mode=signup"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-accent-300 text-primary-900 font-semibold hover:bg-accent-400 transition-colors"
            >
              Get started free
              <ArrowRight size={18} />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center justify-center px-6 py-3 rounded-lg border border-primary-200 text-primary-700 font-semibold hover:bg-primary-50 transition-colors"
            >
              See how it works
            </a>
          </div>
          <p className="text-xs text-primary-400 mt-4">
            No card required. GradScout is completely free.
          </p>
        </Reveal>

        <Reveal delayMs={150}>
          <DedupeVisual />
        </Reveal>
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-white border-y border-primary-100">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 py-20 sm:py-28">
        <Reveal className="max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-primary-400 mb-3">How it works</p>
          <h2 className="font-heading text-3xl sm:text-4xl font-extrabold text-primary-900 tracking-tight">
            Three simple steps
          </h2>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-10 md:gap-8 mt-14 relative">
          {STEPS.map((step, i) => (
            <Reveal key={step.number} delayMs={i * 120}>
              <div className="relative">
                <p className="font-heading text-5xl font-extrabold text-secondary-300 mb-4">{step.number}</p>
                <h3 className="font-heading text-lg font-bold text-primary-900 mb-2">{step.title}</h3>
                <p className="text-sm text-primary-600 leading-relaxed">{step.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Features() {
  return (
    <section id="features" className="max-w-6xl mx-auto px-5 sm:px-8 py-20 sm:py-28">
      <Reveal className="max-w-xl">
        <p className="text-xs font-semibold uppercase tracking-widest text-primary-400 mb-3">Features</p>
        <h2 className="font-heading text-3xl sm:text-4xl font-extrabold text-primary-900 tracking-tight">
          Everything built around one feed
        </h2>
      </Reveal>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-14">
        {FEATURES.map(({ icon: Icon, title, body }, i) => (
          <Reveal key={title} delayMs={(i % 3) * 100}>
            <div className="h-full bg-white rounded-2xl shadow-sm border border-primary-100 p-6 hover:shadow-md transition-shadow">
              <span className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-secondary-100 text-secondary-800 mb-4">
                <Icon size={20} />
              </span>
              <h3 className="font-heading text-base font-bold text-primary-900 mb-1.5">{title}</h3>
              <p className="text-sm text-primary-600 leading-relaxed">{body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  )
}

function Sources() {
  return (
    <section id="sources" className="bg-primary-900">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 py-20 sm:py-28">
        <Reveal className="max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-secondary-300 mb-3">Where we look</p>
          <h2 className="font-heading text-3xl sm:text-4xl font-extrabold text-background tracking-tight">
            Real listings from trusted sources
          </h2>
          <p className="text-primary-200 mt-4 leading-relaxed">
            GradScout uses official job board sources rather than screen-scraping personal sites.
            Every listing takes you straight to where it was originally posted - you always apply
            on the real site, never inside GradScout.
          </p>
        </Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-12 max-w-4xl">
          {SOURCES.map((source, i) => (
            <Reveal key={source.name} delayMs={i * 90}>
              <div className="bg-primary-800 border border-primary-700 rounded-2xl p-5 h-full">
                <p className="font-heading text-base font-bold text-background">{source.name}</p>
                <p className="text-sm text-primary-300 mt-1.5 leading-relaxed">{source.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function FaqSection() {
  return (
    <section id="faq" className="max-w-3xl mx-auto px-5 sm:px-8 py-20 sm:py-28">
      <Reveal>
        <p className="text-xs font-semibold uppercase tracking-widest text-primary-400 mb-3">FAQ</p>
        <h2 className="font-heading text-3xl sm:text-4xl font-extrabold text-primary-900 tracking-tight mb-10">
          Good questions
        </h2>
      </Reveal>
      <Reveal delayMs={100}>
        <Faq items={FAQ_ITEMS} />
      </Reveal>
    </section>
  )
}

function FinalCta() {
  return (
    <section className="border-t border-primary-100">
      <div className="max-w-4xl mx-auto px-5 sm:px-8 py-20 sm:py-28 text-center">
        <Reveal>
          <h2 className="font-heading text-3xl sm:text-4xl font-extrabold text-primary-900 tracking-tight">
            Set your search up once. Let it run.
          </h2>
          <p className="text-primary-600 mt-4 max-w-md mx-auto leading-relaxed">
            It takes about a minute to tell GradScout what you're looking for - the scanning
            happens on its own from there.
          </p>
          <Link
            to="/app/login?mode=signup"
            className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-lg bg-accent-300 text-primary-900 font-semibold hover:bg-accent-400 transition-colors mt-8"
          >
            Get started free
            <ArrowRight size={18} />
          </Link>
        </Reveal>
      </div>
    </section>
  )
}
