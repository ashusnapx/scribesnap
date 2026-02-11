"use client";

import * as React from "react";
import { useInView } from "react-intersection-observer";
import { LayoutGrid, List, Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useNoteHistory } from "@/hooks/useNoteHistory";
import { NoteCard } from "./NoteCard";
import { EmptyState } from "./EmptyState";
import { cn } from "@/lib/utils";
// import { DatePickerWithRange } from "@/components/ui/date-range-picker" // TODO: Add date picker later if needed

export function NoteGrid() {
  const [view, setView] = React.useState<"grid" | "list">("grid");
  const { ref, inView } = useInView();

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, status } =
    useNoteHistory();

  // Infinite scroll trigger
  React.useEffect(() => {
    if (inView && hasNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, fetchNextPage]);

  const isEmpty = status === "success" && data?.pages[0].notes.length === 0;

  if (status === "pending") {
    return (
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
        {[...Array(6)].map((_, i) => (
          <div key={i} className='h-64 rounded-xl bg-muted/50 animate-pulse' />
        ))}
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className='text-center py-20 text-destructive'>
        <p>Failed to load notes. Please try again later.</p>
      </div>
    );
  }

  if (isEmpty) {
    return <EmptyState />;
  }

  return (
    <div className='space-y-8'>
      {/* Toolbar */}
      <div className='flex flex-col sm:flex-row gap-4 items-center justify-between sticky top-20 z-10 bg-background/80 backdrop-blur-md p-4 rounded-xl border border-border/50 shadow-sm'>
        <div className='relative w-full sm:w-72'>
          <Search className='absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground' />
          <Input
            placeholder='Search notes...'
            className='pl-9 bg-muted/50 border-transparent focus:border-primary/50 focus:bg-background transition-all'
          />
        </div>

        <div className='flex items-center gap-2'>
          <ToggleGroup
            type='single'
            value={view}
            onValueChange={(v) => v && setView(v as any)}
          >
            <ToggleGroupItem value='grid' aria-label='Grid view'>
              <LayoutGrid className='w-4 h-4' />
            </ToggleGroupItem>
            <ToggleGroupItem value='list' aria-label='List view'>
              <List className='w-4 h-4' />
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      </div>

      {/* Grid */}
      <div
        className={cn(
          "grid gap-6",
          view === "grid" ?
            "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
          : "grid-cols-1",
        )}
      >
        {data?.pages.map((page, i) => (
          <React.Fragment key={i}>
            {page.notes.map((note, index) => (
              <NoteCard key={note.id} note={note} index={index % 20} />
            ))}
          </React.Fragment>
        ))}
      </div>

      {/* Loading More Indicator */}
      <div ref={ref} className='py-8 flex justify-center'>
        {isFetchingNextPage && (
          <Loader2 className='w-6 h-6 animate-spin text-muted-foreground' />
        )}
      </div>
    </div>
  );
}
