"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ParseResponse, ApiError } from "@/lib/types";

interface UseParseNoteOptions {
  onSuccess?: (data: ParseResponse) => void;
  onError?: (error: ApiError) => void;
}

export function useParseNote(options: UseParseNoteOptions = {}) {
  return useMutation<ParseResponse, ApiError, File>({
    mutationFn: (file: File) => api.upload<ParseResponse>("/api/parse", file),
    onSuccess: (data) => {
      options.onSuccess?.(data);
    },
    onError: (error) => {
      console.error("Parse failed:", error);
      options.onError?.(error);
    },
  });
}
