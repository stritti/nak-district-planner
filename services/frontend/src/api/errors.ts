export class UnauthorizedError extends Error {
  constructor(cause?: unknown) {
    super('Unauthorized - please log in again', { cause })
    this.name = 'UnauthorizedError'
  }
}
