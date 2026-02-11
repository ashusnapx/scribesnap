"use client";

import * as React from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { NoteListResponse, ApiError } from "@/lib/types";

interface UseNoteHistoryOptions {
  limit?: number;
  fromDate?: string;
  toDate?: string;
  sort?: "created_at_desc" | "created_at_asc";
}

export function useNoteHistory({
  limit = 20,
  fromDate,
  toDate,
  sort = "created_at_desc",
}: UseNoteHistoryOptions = {}) {
  return useInfiniteQuery<NoteListResponse, ApiError>({
    queryKey: ["notes", { limit, fromDate, toDate, sort }],
    queryFn: async ({ pageParam }) => {
      const params: Record<string, any> = {
        limit,
        sort,
        from_date: fromDate,
        to_date: toDate,
      };

      if (pageParam) {
        params.cursor = pageParam;
      }

      return api.get<NoteListResponse>("/api/notes", params);
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor : undefined,
  });
}
