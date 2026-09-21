import type { H3Event } from 'h3'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

/** Uniform JSON error body: {"error": "..."} */
export function sendApiError(event: H3Event, err: unknown) {
  const status = err instanceof ApiError ? err.status : 500
  const message = err instanceof Error ? err.message : 'internal error'
  if (status >= 500) console.error('[api]', err)
  setResponseStatus(event, status)
  return { error: message }
}
