export default function Footer() {
  return (
    <footer className="border-t border-white/5 px-6 py-8">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-6 w-6 rounded-md bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-xs">A</span>
          </div>
          <span className="text-sm text-[var(--color-text-muted)]">Aureon — AI-Powered Urban Intelligence</span>
        </div>
        <p className="text-xs text-[var(--color-text-muted)]">
          &copy; {new Date().getFullYear()} Aureon. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
