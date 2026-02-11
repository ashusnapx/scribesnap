/**
 * API Client
 * ==========
 *
 * Typed wrapper around fetch for communicating with the FastAPI backend.
 * Handles base URL, common headers, and error parsing.
 */

import { ApiError } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // Handle non-2xx responses
      if (!response.ok) {
        let errorData: ApiError;
        try {
          errorData = await response.json();
        } catch {
          // Fallback if response isn't JSON
          errorData = {
            error: "unknown_error",
            message: response.statusText || "An unexpected error occurred",
          };
        }
        throw errorData;
      }

      // Handle empty bodies (e.g. 204 No Content)
      if (response.status === 204) {
        return {} as T;
      }

      return response.json();
    } catch (error) {
      // Re-throw ApiErrors, wrap others
      if ((error as ApiError).error) {
        throw error;
      }
      throw {
        error: "network_error",
        message:
          error instanceof Error ? error.message : "Network request failed",
      } as ApiError;
    }
  }

  // ── Public Methods ────────────────────────────────────────────────────────

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    let queryString = "";
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      queryString = `?${searchParams.toString()}`;
    }
    return this.request<T>(`${endpoint}${queryString}`, { method: "GET" });
  }

  async post<T>(endpoint: string, body: any): Promise<T> {
    const isFormData = body instanceof FormData;
    const headers: HeadersInit = {};

    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }

    return this.request<T>(endpoint, {
      method: "POST",
      headers,
      body: isFormData ? body : JSON.stringify(body),
    });
  }

  async upload<T>(endpoint: string, file: File): Promise<T> {
    const formData = new FormData();
    formData.append("file", file);
    return this.post<T>(endpoint, formData);
  }
}

export const api = new ApiClient();
