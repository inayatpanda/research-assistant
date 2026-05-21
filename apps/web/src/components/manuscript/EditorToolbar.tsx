/**
 * Phase 4.5 — Manuscript editor toolbar.
 *
 * Sits above the editor pane between SectionTabs and the EditorContent.
 * Surfaces three new actions that previously had no visible affordance:
 *   • Insert table       (popover with rows/cols inputs + add/remove buttons)
 *   • Insert articles table (multi-step dialog — sibling component)
 *   • Reference a figure (dropdown listing project figures → FigRef node)
 *
 * The buttons mirror commands TipTap already exposes (insertTable, addRowAfter
 * etc.) — the toolbar is purely a discoverability surface; the existing
 * keyboard shortcuts continue to work unchanged.
 */
import type { Editor } from '@tiptap/react'
import { Database, ImageDown, Table as TableIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useFigures } from '@/hooks/useFigures'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

import { InsertArticlesTableDialog } from './InsertArticlesTableDialog'

export function EditorToolbar({
  projectId,
  editor,
}: {
  projectId: string
  editor: Editor | null
}) {
  const [rows, setRows] = useState(3)
  const [cols, setCols] = useState(3)
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [articlesDialogOpen, setArticlesDialogOpen] = useState(false)
  const [figrefMenuOpen, setFigrefMenuOpen] = useState(false)
  const figrefMenuRef = useRef<HTMLDivElement | null>(null)
  const { data: figures = [] } = useFigures(projectId)

  // Click-outside handling for the FigRef menu. Using a plain hand-rolled
  // dropdown (rather than Radix) keeps the menu trivially testable in
  // jsdom without pulling in @testing-library/user-event.
  useEffect(() => {
    if (!figrefMenuOpen) return
    const onDoc = (e: MouseEvent) => {
      if (!figrefMenuRef.current) return
      if (figrefMenuRef.current.contains(e.target as Node)) return
      setFigrefMenuOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [figrefMenuOpen])

  // Table-edit affordances are only meaningful while the cursor is
  // inside a table. ``editor.can()`` returns false outside, so the
  // buttons disable themselves.
  const canEditTable = Boolean(editor?.can().addRowAfter())

  const insertTable = () => {
    if (!editor) return
    const safeRows = Math.max(1, Math.min(20, Math.trunc(rows) || 3))
    const safeCols = Math.max(1, Math.min(10, Math.trunc(cols) || 3))
    editor
      .chain()
      .focus()
      .insertTable({ rows: safeRows, cols: safeCols, withHeaderRow: true })
      .run()
    setPopoverOpen(false)
  }

  const insertFigRef = (figureId: string) => {
    if (!editor) return
    editor.chain().focus().insertFigRef({ figureId }).run()
    setFigrefMenuOpen(false)
  }

  return (
    <div
      className="flex items-center gap-2 border-b border-border bg-zinc-50/60 px-3 py-1.5"
      data-testid="editor-toolbar"
    >
      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger asChild>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-[12px] gap-1"
            aria-label="Insert table"
            disabled={!editor}
          >
            <TableIcon className="h-3.5 w-3.5" /> Table
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 space-y-3" align="start">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Insert table
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor="table-rows" className="text-xs">
                Rows
              </Label>
              <Input
                id="table-rows"
                type="number"
                min={1}
                max={20}
                value={rows}
                onChange={(e) => setRows(parseInt(e.target.value, 10))}
                className="h-7"
              />
            </div>
            <div>
              <Label htmlFor="table-cols" className="text-xs">
                Columns
              </Label>
              <Input
                id="table-cols"
                type="number"
                min={1}
                max={10}
                value={cols}
                onChange={(e) => setCols(parseInt(e.target.value, 10))}
                className="h-7"
              />
            </div>
          </div>
          <Button size="sm" className="w-full" onClick={insertTable}>
            Insert {rows} × {cols} table
          </Button>

          <div className="border-t border-border pt-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
              Edit current table
            </div>
            <div className="grid grid-cols-2 gap-1">
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                disabled={!canEditTable}
                onClick={() => editor?.chain().focus().addRowAfter().run()}
              >
                + Row
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                disabled={!canEditTable}
                onClick={() => editor?.chain().focus().deleteRow().run()}
              >
                − Row
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                disabled={!canEditTable}
                onClick={() => editor?.chain().focus().addColumnAfter().run()}
              >
                + Column
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                disabled={!canEditTable}
                onClick={() => editor?.chain().focus().deleteColumn().run()}
              >
                − Column
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="col-span-2 h-7 text-xs"
                disabled={!canEditTable}
                onClick={() => editor?.chain().focus().deleteTable().run()}
              >
                Delete table
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>

      <Button
        size="sm"
        variant="ghost"
        className="h-7 text-[12px] gap-1"
        aria-label="Insert articles table"
        onClick={() => setArticlesDialogOpen(true)}
        disabled={!editor}
      >
        <Database className="h-3.5 w-3.5" /> Articles table
      </Button>

      <div className="relative" ref={figrefMenuRef}>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 text-[12px] gap-1"
          aria-label="Reference a figure"
          aria-expanded={figrefMenuOpen}
          disabled={!editor}
          onClick={() => setFigrefMenuOpen((v) => !v)}
        >
          <ImageDown className="h-3.5 w-3.5" /> Figure ref
        </Button>
        {figrefMenuOpen && (
          <div
            role="menu"
            data-testid="figref-menu"
            className="absolute left-0 top-full z-50 mt-1 min-w-[260px] max-w-md rounded-md border border-border bg-white shadow-lg py-1"
          >
            <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
              Insert reference to figure
            </div>
            {figures.length === 0 ? (
              <div className="px-2 py-1.5 text-xs text-muted-foreground">
                No figures in this project yet
              </div>
            ) : (
              figures.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  role="menuitem"
                  data-testid={`figref-item-${f.id}`}
                  onClick={() => insertFigRef(f.id)}
                  className="flex w-full flex-col items-start gap-0.5 px-2 py-1.5 text-left hover:bg-muted/30"
                >
                  <span className="text-sm font-medium">
                    Figure {f.figure_number}
                  </span>
                  <span className="text-xs text-muted-foreground truncate max-w-[28ch]">
                    {f.caption || '(no caption)'}
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <InsertArticlesTableDialog
        open={articlesDialogOpen}
        onOpenChange={setArticlesDialogOpen}
        projectId={projectId}
        editor={editor}
      />
    </div>
  )
}
