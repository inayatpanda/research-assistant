import { Link } from 'react-router-dom'

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-slate-200 bg-sidebar text-sidebar-foreground">
      <div className="container-wide grid gap-10 py-12 md:grid-cols-4">
        <div className="md:col-span-2">
          <div className="text-base font-semibold">Research Assistant</div>
          <p className="mt-3 max-w-md text-sm text-white/70">
            A local-first manuscript assistant for clinical research. Free, open source,
            no telemetry, runs entirely on your laptop.
          </p>
        </div>
        <div>
          <div className="text-sm font-semibold text-white/90">Product</div>
          <ul className="mt-3 space-y-2 text-sm text-white/70">
            <li>
              <Link to="/install" className="hover:text-white">
                Install
              </Link>
            </li>
            <li>
              <Link to="/sync" className="hover:text-white">
                Sync to iPad
              </Link>
            </li>
            <li>
              <Link to="/docs" className="hover:text-white">
                Docs &amp; FAQ
              </Link>
            </li>
            <li>
              <Link to="/changelog" className="hover:text-white">
                Changelog
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <div className="text-sm font-semibold text-white/90">Resources</div>
          <ul className="mt-3 space-y-2 text-sm text-white/70">
            <li>
              <a
                href="https://github.com/TBD-OWNER/TBD-REPO"
                className="hover:text-white"
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
            </li>
            <li>
              <a
                href="https://github.com/TBD-OWNER/TBD-REPO/releases"
                className="hover:text-white"
                target="_blank"
                rel="noreferrer"
              >
                Releases
              </a>
            </li>
            <li>
              <a
                href="https://github.com/TBD-OWNER/TBD-REPO/issues"
                className="hover:text-white"
                target="_blank"
                rel="noreferrer"
              >
                Report a bug
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="container-wide flex flex-col items-start justify-between gap-2 py-6 text-xs text-white/50 sm:flex-row sm:items-center">
          <span>© {new Date().getFullYear()} Research Assistant contributors.</span>
          <span>Free + open source. Your data lives on your laptop.</span>
        </div>
      </div>
    </footer>
  )
}
