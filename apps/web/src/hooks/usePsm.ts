import { useMutation, useQueryClient } from '@tanstack/react-query'

import { psmApi, type PSMRequest, type PSMResponse } from '@/lib/api'

export function usePsm(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation<PSMResponse, Error, PSMRequest>({
    mutationFn: (body) => psmApi.run(projectId, datasetId, body),
    onSuccess: () => {
      // A new derived Dataset row is created server-side; refresh listings.
      qc.invalidateQueries({ queryKey: ['datasets', projectId] })
    },
  })
}
