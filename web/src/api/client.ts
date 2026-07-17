import { ApiError } from './errors'

export type InstallationSummary = {
  catalog_status: string
  default_translation_id: string | null
  default_translation_name: string | null
  installed_translations: Array<{
    translation_id: string
    psalm_count: number
    is_default: boolean
  }>
  is_ready: boolean
  last_error: string | null
}

type ErrorPayload = {
  error?: {
    message?: string
    request_id?: string | null
    details?: unknown
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (response.ok) {
    return (await response.json()) as T
  }

  const payload = (await response.json().catch(() => ({}))) as ErrorPayload
  throw new ApiError(
    payload.error?.message ?? `Request failed with status ${response.status}.`,
    response.status,
    payload.error?.request_id ?? null,
    payload.error?.details ?? null,
  )
}

export function getInstallation(): Promise<InstallationSummary> {
  return request<InstallationSummary>('/api/v1/installation')
}
