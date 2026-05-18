import { describe, expect, it } from 'vitest'

import { FigureSchema } from '../api'

describe('FigureSchema', () => {
  it('parses a server payload', () => {
    const parsed = FigureSchema.parse({
      id: 'f1',
      project_id: 'p1',
      figure_number: 1,
      caption: 'Knee MRI',
      alt_text: 'Coronal MRI of left knee',
      file_type: 'image/png',
      width_px: 800,
      height_px: 600,
      byte_size: 100_000,
      file_url: '/files/abc.token',
      created_at: '2026-05-18T00:00:00Z',
      updated_at: '2026-05-18T00:01:00Z',
    })
    expect(parsed.figure_number).toBe(1)
    expect(parsed.file_type).toBe('image/png')
  })

  it('allows file_url to be null', () => {
    const parsed = FigureSchema.parse({
      id: 'f1', project_id: 'p1', figure_number: 1, caption: '', alt_text: '',
      file_type: 'image/svg+xml', width_px: null, height_px: null,
      byte_size: 200, file_url: null,
      created_at: '2026-05-18T00:00:00Z',
      updated_at: '2026-05-18T00:01:00Z',
    })
    expect(parsed.width_px).toBeNull()
  })

  it('rejects unknown file_type', () => {
    expect(() =>
      FigureSchema.parse({
        id: 'f', project_id: 'p', figure_number: 1, caption: '', alt_text: '',
        file_type: 'application/pdf', width_px: null, height_px: null,
        byte_size: 1,
        created_at: '2026-05-18T00:00:00Z',
        updated_at: '2026-05-18T00:00:00Z',
      }),
    ).toThrow()
  })
})
