import { ApiError } from './errors'

export type InstallationSummary = {
  catalog_status: string
  scripture_provider: string
  default_translation_id: string | null
  default_translation_name: string | null
  updated_at?: string | null
  installed_translations: Array<{
    translation_id: string
    psalm_count: number
    is_default: boolean
  }>
  is_ready: boolean
  last_error: string | null
}

export type TranslationSummary = {
  id: string
  name: string
  language: string
  supports_psalms: boolean
}

export type PsalmProgressSummary = {
  psalm_id: string
  translation_id: string
  psalm_number: number
  status: string
  section_count: number
  sections_learned: number
  current_section_label: string | null
  reviews_due: number
  consolidation_available: boolean
}

export type PsalmListItem = {
  id: string
  translation_id: string
  psalm_number: number
  verse_count: number
  completeness: string
  learning: PsalmProgressSummary
}

export type PsalmDetail = {
  id: string
  translation_id: string
  psalm_number: number
  canonical_text: string
  verse_count: number
  completeness: string
  verses: Array<{
    verse_number: number
    canonical_text: string
  }>
  learning: PsalmProgressSummary
}

export type ReviewItem = {
  psalm_id: string
  translation_id: string
  psalm_number: number
  reason: string
  due_label: string
  next_review_at: string | null
  passage_id: string
}

export type ProgressSummary = {
  total_passages: number
  unseen_passages: number
  exposure_passages: number
  practice_passages: number
  ready_passages: number
  reinforcement_passages: number
  learned_passages: number
  reviews_due: number
  total_recitation_attempts: number
  successful_recitation_attempts: number
}

export type ProgressPayload = {
  summary: ProgressSummary
  psalms: PsalmProgressSummary[]
}

export type SettingsPayload = {
  catalog_status: string
  scripture_provider: string
  default_translation_id: string | null
  default_translation_name: string | null
  initialized_at: string | null
  last_error: string | null
  installed_translations: Array<{
    translation_id: string
    psalm_count: number
    is_default: boolean
  }>
  log_level: string
}

export type LearningScreen = {
  screen: string
  psalm_number: number
  translation_id: string
  status: string
  section_count: number
  sections_learned: number
  consolidation_available: boolean
  active_target: {
    token: string
    label: string
    kind: string
  } | null
  active_passage: {
    id: string
    start_verse: number
    end_verse: number
    canonical_text: string
    kind: string
  } | null
  practice: {
    masked_text: string
    level: number
    max_level: number
  } | null
  assessment: {
    result: string
    weighted_accuracy: number
    omission_count: number
    substitution_count: number
    insertion_count: number
    longest_omitted_span: number
    remaining_successes_required: number
  } | null
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

export async function getTranslations(): Promise<TranslationSummary[]> {
  const payload = await request<{ items: TranslationSummary[] }>('/api/v1/translations')
  return payload.items
}

export async function getPsalms(): Promise<PsalmListItem[]> {
  const payload = await request<{ items: PsalmListItem[] }>('/api/v1/psalms')
  return payload.items
}

export function getPsalm(psalmNumber: number): Promise<PsalmDetail> {
  return request<PsalmDetail>(`/api/v1/psalms/${psalmNumber}`)
}

export function getProgress(): Promise<ProgressPayload> {
  return request<ProgressPayload>('/api/v1/progress')
}

export async function getReviews(): Promise<ReviewItem[]> {
  const payload = await request<{ items: ReviewItem[] }>('/api/v1/reviews')
  return payload.items
}

export function getSettings(): Promise<SettingsPayload> {
  return request<SettingsPayload>('/api/v1/settings')
}

type LearningMutation = {
  translation_id?: string
  target_token?: string
}

export function getLearningState(psalmNumber: number): Promise<LearningScreen> {
  return request<LearningScreen>(`/api/v1/psalms/${psalmNumber}/learning`)
}

export function startLearning(
  psalmNumber: number,
  payload?: LearningMutation,
): Promise<LearningScreen> {
  return request<LearningScreen>(`/api/v1/psalms/${psalmNumber}/learning/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload ?? {}),
  })
}

export function completeExposure(
  psalmNumber: number,
  payload: LearningMutation,
): Promise<LearningScreen> {
  return request<LearningScreen>(`/api/v1/psalms/${psalmNumber}/learning/exposure/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function completePractice(
  psalmNumber: number,
  payload: LearningMutation,
): Promise<LearningScreen> {
  return request<LearningScreen>(`/api/v1/psalms/${psalmNumber}/learning/practice/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function resumeReinforcement(
  psalmNumber: number,
  payload: LearningMutation,
): Promise<LearningScreen> {
  return request<LearningScreen>(
    `/api/v1/psalms/${psalmNumber}/learning/reinforcement/resume`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
}

export function submitTypedRecitation(
  psalmNumber: number,
  payload: LearningMutation & { text: string },
): Promise<LearningScreen> {
  return request<LearningScreen>(`/api/v1/psalms/${psalmNumber}/learning/recitations/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function submitAudioRecitation(
  psalmNumber: number,
  payload: FormData,
): Promise<LearningScreen> {
  const response = await fetch(`/api/v1/psalms/${psalmNumber}/learning/recitations/audio`, {
    method: 'POST',
    body: payload,
  })

  if (response.ok) {
    return (await response.json()) as LearningScreen
  }

  const errorPayload = (await response.json().catch(() => ({}))) as ErrorPayload
  throw new ApiError(
    errorPayload.error?.message ?? `Request failed with status ${response.status}.`,
    response.status,
    errorPayload.error?.request_id ?? null,
    errorPayload.error?.details ?? null,
  )
}

type InstallationMutation = {
  translation_id?: string
  set_as_default?: boolean
}

export function initializeInstallation(payload: InstallationMutation): Promise<InstallationSummary> {
  return request<InstallationSummary>('/api/v1/installation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function resumeInstallation(payload: InstallationMutation): Promise<InstallationSummary> {
  return request<InstallationSummary>('/api/v1/installation/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function repairInstallation(payload: InstallationMutation): Promise<InstallationSummary> {
  return request<InstallationSummary>('/api/v1/installation/repair', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
