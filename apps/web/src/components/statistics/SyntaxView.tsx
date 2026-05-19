import { Check, Code2, Copy } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import type { Analysis, Dataset, TransformationRead } from '@/lib/api'
import { renderSyntax } from '@/lib/syntaxRenderer'

export function SyntaxView({
  dataset,
  transformations,
  analyses,
}: {
  dataset: Dataset | null | undefined
  transformations: TransformationRead[] | null | undefined
  analyses?: Analysis[] | null
}) {
  const [copied, setCopied] = useState(false)
  const text = useMemo(
    () => renderSyntax(dataset, transformations, analyses),
    [dataset, transformations, analyses],
  )

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // clipboard unavailable; silently ignore.
    }
  }

  return (
    <div className="rounded-lg border border-border bg-white overflow-hidden">
      <header className="flex items-center justify-between gap-2 px-3 py-2 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          <Code2 className="h-3.5 w-3.5" />
          Syntax
        </div>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-[12px]"
          onClick={onCopy}
          aria-label="Copy syntax to clipboard"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 mr-1" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5 mr-1" /> Copy
            </>
          )}
        </Button>
      </header>
      <pre className="px-3 py-3 text-[12px] leading-relaxed font-mono whitespace-pre-wrap break-words text-foreground">
        {text}
      </pre>
    </div>
  )
}
