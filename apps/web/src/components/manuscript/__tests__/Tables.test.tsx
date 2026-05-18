import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { Table } from '@tiptap/extension-table'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableRow } from '@tiptap/extension-table-row'
import { describe, expect, it } from 'vitest'

describe('TipTap table extensions', () => {
  it('inserts a 2x2 table with a header row', () => {
    const ed = new Editor({
      extensions: [
        StarterKit,
        Table.configure({ HTMLAttributes: { class: 'rma-table' } }),
        TableRow,
        TableHeader,
        TableCell,
      ],
      content: '',
    })
    ed.commands.insertTable({ rows: 2, cols: 2, withHeaderRow: true })
    const html = ed.getHTML()
    expect(html).toContain('<table')
    expect(html).toContain('rma-table')
    expect(html).toContain('<th')
    ed.destroy()
  })

  it('round-trips table HTML through getHTML', () => {
    const ed = new Editor({
      extensions: [StarterKit, Table, TableRow, TableHeader, TableCell],
      content:
        '<table><tbody><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></tbody></table>',
    })
    const html = ed.getHTML()
    expect(html).toContain('A')
    expect(html).toContain('B')
    expect(html).toContain('1')
    expect(html).toContain('2')
    ed.destroy()
  })
})
