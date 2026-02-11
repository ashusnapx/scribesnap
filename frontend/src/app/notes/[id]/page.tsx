/**
 * Note Detail Page
 * =================
 *
 * Displays full details of a single note.
 * Uses server component for initial data fetching (future optimization),
 * but fundamentally client-side for this MVP iteration.
 */

"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Calendar,
  FileText,
  Download,
  Share2,
  Sparkles,
  AlertTriangle,
  Check,
  Copy,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Note } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDate, getApiUrl, copyToClipboard } from "@/lib/utils";

export default function NoteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: note,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["note", id],
    queryFn: () => api.get<Note>(`/api/notes/${id}`),
    retry: 1,
  });

  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    if (!note) return;
    try {
      await copyToClipboard(note.parsed_text);
      setCopied(true);
      toast.success("Text copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy text");
    }
  };

  const handleDownload = (format: "txt" | "md") => {
    if (!note) return;
    const element = document.createElement("a");
    const file = new Blob([note.parsed_text], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = `scribesnap-note-${note.id}.${format}`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    toast.success(`Downloaded as .${format}`);
  };

  const handleShare = async () => {
    if (!note) return;
    if (navigator.share) {
      try {
        await navigator.share({
          title: "ScribeSnap Note",
          text: note.parsed_text,
          url: window.location.href,
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          toast.error("Failed to share");
        }
      }
    } else {
      handleCopy();
      toast.info("Web Share not supported - copied to clipboard instead");
    }
  };

  if (isLoading) {
    return (
      <div className='container mx-auto px-4 py-8 max-w-5xl space-y-8'>
        <div className='flex items-center gap-4'>
          <Skeleton className='h-10 w-10 rounded-full' />
          <Skeleton className='h-8 w-40' />
        </div>
        <div className='grid md:grid-cols-2 gap-8'>
          <Skeleton className='h-[500px] w-full rounded-xl' />
          <div className='space-y-4'>
            <Skeleton className='h-8 w-3/4' />
            <Skeleton className='h-[400px] w-full rounded-xl' />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='container mx-auto px-4 py-20 flex flex-col items-center text-center max-w-lg'>
        <div className='w-16 h-16 bg-destructive/10 text-destructive rounded-full flex items-center justify-center mb-6'>
          <AlertTriangle className='w-8 h-8' />
        </div>
        <h1 className='text-2xl font-bold mb-2'>Note not found</h1>
        <p className='text-muted-foreground mb-6'>
          The note you are looking for does not exist or has been deleted.
        </p>
        <Button onClick={() => router.push("/history")} variant='default'>
          Return to History
        </Button>
      </div>
    );
  }

  if (!note) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className='container mx-auto px-4 py-8 max-w-6xl'
    >
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8'>
        <Button
          variant='ghost'
          className='w-fit -ml-2 text-muted-foreground hover:text-foreground'
          onClick={() => router.back()}
        >
          <ArrowLeft className='w-4 h-4 mr-2' />
          Back
        </Button>

        <div className='flex items-center gap-2'>
          <Badge
            variant={note.status === "completed" ? "secondary" : "destructive"}
          >
            {note.status}
          </Badge>
          <span className='text-sm text-muted-foreground flex items-center gap-1 bg-muted/50 px-3 py-1 rounded-full'>
            <Calendar className='w-3.5 h-3.5' />
            {formatDate(note.created_at)}
          </span>
        </div>
      </div>

      <div className='grid lg:grid-cols-2 gap-8'>
        {/* Left: Image */}
        <div className='space-y-4'>
          <h2 className='text-lg font-semibold flex items-center gap-2'>
            <FileText className='w-5 h-5 text-primary' />
            Original Image
          </h2>
          <Card className='overflow-hidden bg-muted/30 border-muted p-2 h-[600px] flex items-center justify-center relative group'>
            {/* Overlay pattern */}
            <div className='absolute inset-0 bg-grid-black/[0.02] dark:bg-grid-white/[0.02]' />

            <img
              src={getApiUrl(note.image_url)}
              alt='Original note'
              className='max-w-full max-h-full object-contain rounded-lg shadow-sm'
            />
          </Card>
        </div>

        {/* Right: Text */}
        <div className='space-y-4 flex flex-col h-full'>
          <div className='flex items-center justify-between'>
            <h2 className='text-lg font-semibold flex items-center gap-2'>
              <Sparkles className='w-5 h-5 text-primary' />
              Parsed Text
            </h2>
            <div className='flex gap-2'>
              <Button
                variant='outline'
                size='sm'
                className='gap-2 rounded-full h-8'
                onClick={handleShare}
              >
                <Share2 className='w-3.5 h-3.5' />
                Share
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant='outline'
                    size='sm'
                    className='gap-2 rounded-full h-8'
                  >
                    <Download className='w-3.5 h-3.5' />
                    Download
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align='end'>
                  <DropdownMenuItem onClick={() => handleDownload("txt")}>
                    Plain Text (.txt)
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleDownload("md")}>
                    Markdown (.md)
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <Button
                variant='outline'
                size='sm'
                className='gap-2 rounded-full h-8'
                onClick={handleCopy}
              >
                {copied ?
                  <Check className='w-3.5 h-3.5' />
                : <Copy className='w-3.5 h-3.5' />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>

          <Card className='flex-1 p-6 bg-background/50 backdrop-blur-sm border-primary/10 overflow-auto max-h-[600px] shadow-inner relative'>
            <pre className='whitespace-pre-wrap font-mono text-sm leading-relaxed text-foreground/90 font-light'>
              {note.parsed_text}
            </pre>
          </Card>
        </div>
      </div>
    </motion.div>
  );
}
