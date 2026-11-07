export class ApiConflictError extends Error {
  readonly status = 409
  readonly code = 'conflict' as const

  constructor(message: string) {
    super(message)
    this.name = 'ApiConflictError'
  }
}

export function isApiConflictError(error: unknown): error is ApiConflictError {
  return error instanceof ApiConflictError
}
