import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { projectsApi, ProjectCreateSchema, type ProjectCreate } from '@/lib/api'
import { studyTypes } from '@/lib/tokens'

export function CreateProjectDialog() {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [studyType, setStudyType] = useState<ProjectCreate['study_type']>('Outcome Study')
  const qc = useQueryClient()

  const { mutate, isPending } = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project created')
      setOpen(false)
      setTitle('')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const parsed = ProjectCreateSchema.safeParse({
      title: title.trim(),
      study_type: studyType,
    })
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? 'Invalid input')
      return
    }
    mutate(parsed.data)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-accent hover:bg-accent-hover text-white">
          <Plus className="h-4 w-4 mr-1.5" />
          New project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[460px]">
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>
              Set a title and study type. You can change these later.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="mt-2 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Anterior approach vs posterior approach in THA"
                autoFocus
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="study-type">Study type</Label>
              <Select
                value={studyType}
                onValueChange={(v) => setStudyType(v as ProjectCreate['study_type'])}
              >
                <SelectTrigger id="study-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {studyTypes.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isPending}
                className="bg-accent hover:bg-accent-hover text-white"
              >
                {isPending ? 'Creating…' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </motion.div>
      </DialogContent>
    </Dialog>
  )
}
