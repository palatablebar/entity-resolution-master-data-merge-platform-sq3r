export interface ApiErrorShape {
  code: string;
  message: string;
  detail?: string;
  trace_id?: string | null;
  extra?: Record<string, unknown>;
}

export class ApiError extends Error {
  status: number;
  payload: ApiErrorShape;

  constructor(status: number, payload: ApiErrorShape) {
    super(payload.message || `HTTP ${status}`);
    this.status = status;
    this.payload = payload;
  }
}
