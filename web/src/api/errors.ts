export class ApiError extends Error {
  status: number
  requestId: string | null
  details: unknown

  constructor(message: string, status: number, requestId: string | null, details: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.requestId = requestId
    this.details = details
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred.'
}
