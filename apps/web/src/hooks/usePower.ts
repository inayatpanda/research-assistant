import { useMutation } from '@tanstack/react-query'

import { powerApi, type PowerRequest, type PowerResponse } from '@/lib/api'

export function usePower() {
  return useMutation<PowerResponse, Error, PowerRequest>({
    mutationFn: (body) => powerApi.calculate(body),
  })
}
