export default function App() {
  return (
    <div className="min-h-screen bg-workspace text-foreground">
      <div className="p-8">
        <h1 className="text-2xl font-semibold">Research Manuscript Assistant</h1>
        <p className="mt-2 text-sm text-muted-foreground">Phase 1 — scaffold check</p>
        <div className="mt-4 flex gap-2">
          <div className="h-6 w-6 rounded bg-highlight-intro" />
          <div className="h-6 w-6 rounded bg-highlight-method" />
          <div className="h-6 w-6 rounded bg-highlight-results" />
          <div className="h-6 w-6 rounded bg-highlight-discussion" />
        </div>
      </div>
    </div>
  )
}
