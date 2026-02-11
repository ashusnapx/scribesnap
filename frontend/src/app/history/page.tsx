import { Metadata } from "next";
import { NoteGrid } from "@/components/notes/NoteGrid";

export const metadata: Metadata = {
  title: "History - ScribeSnap",
  description: "View your previously parsed handwritten notes.",
};

export default function HistoryPage() {
  return (
    <div className='container mx-auto px-4 py-8 max-w-7xl'>
      <div className='mb-8 space-y-2'>
        <h1 className='text-3xl font-bold tracking-tight'>Your Notes</h1>
        <p className='text-muted-foreground'>
          Manage and search your previously scanned handwritten notes.
        </p>
      </div>

      <NoteGrid />
    </div>
  );
}
