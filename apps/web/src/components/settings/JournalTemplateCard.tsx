import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useJournalTemplates } from '@/hooks/useJournalTemplates'
import { projectsApi } from '@/lib/api'

export function JournalTemplateCard({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })
  const { data: templates = [] } = useJournalTemplates()

  const mut = useMutation({
    mutationFn: (template_journal: string | null) =>
      projectsApi.update(projectId, { template_journal }),
    onSuccess: (p) => {
      qc.setQueryData(['project', projectId], p)
      toast.success('Template updated')
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : 'Update failed'),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-[15px]">Target journal template</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-[13px]">
        <p className="text-muted-foreground">
          Picking a template tells the word-count bar what to compare against.
          Word and figure limits are advisory.
        </p>
        <label className="block">
          <span className="font-medium">Template</span>
          <select
            value={project?.template_journal ?? ''}
            onChange={(e) => mut.mutate(e.target.value === '' ? null : e.target.value)}
            className="mt-1 block w-full rounded border border-border px-2 py-1.5 text-sm"
          >
            <option value="">No template</option>
            {templates.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        {project?.template_journal && (
          <div className="text-xs text-muted-foreground">
            Current: <code>{project.template_journal}</code>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
