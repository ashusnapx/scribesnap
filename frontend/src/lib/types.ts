/**
 * Shared Type Definitions
 * =======================
 *
 * Matches backend Pydantic models from `backend/app/schemas/note.py`.
 * Keeps frontend and backend data structures in sync.
 */

export type NoteStatus = "processing" | "completed" | "failed";

export interface Note {
  id: string;
  image_url: string;
  parsed_text: string;
  created_at: string; // ISO 8601
  status: NoteStatus;
  error_message?: string | null;
}

export interface NoteListItem {
  id: string;
  image_url: string;
  text_preview: string;
  created_at: string;
  status: NoteStatus;
}

export interface NoteListResponse {
  notes: NoteListItem[];
  total_count: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface ParseResponse {
  message: string;
  parsed_text: string;
  note: Note;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  gemini: string;
  uptime_seconds: number;
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, any>;
  request_id?: string;
}
