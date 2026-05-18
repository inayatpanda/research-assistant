import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'

import { useUpdateFigure, useUploadFigure } from '@/hooks/useFigures'

export function FigureUploadDialog({
  projectId,
  onClose,
}: {
  projectId: string
  onClose: () => void
}) {
  const upload = useUploadFigure(projectId)
  const patch = useUpdateFigure(projectId)

  const [uploadedId, setUploadedId] = useState<string | null>(null)
  const [caption, setCaption] = useState('')
  const [altText, setAltText] = useState('')

  const onDrop = useCallback(
    async (files: File[]) => {
      const file = files[0]
      if (!file) return
      try {
        const fig = await upload.mutateAsync(file)
        setUploadedId(fig.id)
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'Upload failed')
      }
    },
    [upload],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/svg+xml': ['.svg'],
    },
    multiple: false,
  })

  const saveAndClose = async () => {
    if (uploadedId) {
      try {
        await patch.mutateAsync({
          id: uploadedId,
          body: { caption, alt_text: altText },
        })
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'Save failed')
        return
      }
    }
    onClose()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Upload figure"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    >
      <div className="bg-white rounded-lg shadow-xl p-6 w-[520px] max-w-[90vw]">
        <h2 className="text-lg font-semibold mb-3">Add a figure</h2>
        {uploadedId ? (
          <div className="space-y-3">
            <label className="block">
              <span className="text-sm font-medium">Caption</span>
              <textarea
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="Figure 1. Description of the figure…"
                className="mt-1 block w-full rounded border border-border px-2 py-1 text-sm"
                rows={3}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium">Alt text (≤500 chars)</span>
              <input
                value={altText}
                maxLength={500}
                onChange={(e) => setAltText(e.target.value)}
                placeholder="Plain-language description for screen readers"
                className="mt-1 block w-full rounded border border-border px-2 py-1 text-sm"
              />
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded border border-border text-sm"
              >
                Skip
              </button>
              <button
                onClick={saveAndClose}
                className="px-3 py-1.5 rounded bg-zinc-900 text-white text-sm"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded p-8 text-center cursor-pointer transition ${
                isDragActive ? 'border-zinc-900 bg-zinc-50' : 'border-border'
              }`}
            >
              <input {...getInputProps()} />
              <p className="text-sm text-muted-foreground">
                Drop a PNG, JPEG, or SVG (≤10 MiB) here, or click to browse.
              </p>
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded border border-border text-sm"
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
