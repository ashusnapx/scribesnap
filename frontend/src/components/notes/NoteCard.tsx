"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Clock, FileText, ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { NoteListItem } from "@/lib/types";
import { formatRelativeTime } from "@/lib/utils";

interface NoteCardProps {
  note: NoteListItem;
  index?: number;
}

export function NoteCard({ note, index = 0 }: NoteCardProps) {
  return (
    <Link href={`/notes/${note.id}`}>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: index * 0.05 }}
        whileHover={{ y: -4, transition: { duration: 0.2 } }}
      >
        <Card className='glass-card overflow-hidden h-full flex flex-col group border-transparent hover:border-primary/20'>
          {/* Image Thumbnail Area */}
          <div className='relative h-48 w-full bg-muted overflow-hidden'>
            <img
              src={note.image_url}
              alt='Note thumbnail'
              className='w-full h-full object-cover transition-transform duration-500 group-hover:scale-105'
              loading='lazy'
            />
            <div className='absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end justify-center pb-4'>
              <span className='text-white text-sm font-medium flex items-center gap-1'>
                View Details <ArrowRight className='w-3 h-3' />
              </span>
            </div>
          </div>

          {/* Content Area */}
          <div className='p-4 flex-1 flex flex-col gap-3'>
            <div className='flex items-center justify-between'>
              <Badge
                variant={
                  note.status === "completed" ? "secondary" : "destructive"
                }
                className='text-[10px] px-2 h-5'
              >
                {note.status}
              </Badge>
              <span className='text-xs text-muted-foreground flex items-center gap-1'>
                <Clock className='w-3 h-3' />
                {formatRelativeTime(note.created_at)}
              </span>
            </div>

            <div className='relative flex-1'>
              <p className='text-sm text-foreground/80 line-clamp-3 leading-relaxed font-mono'>
                {note.text_preview || (
                  <span className='italic text-muted-foreground'>
                    No text content...
                  </span>
                )}
              </p>
              {/* Fade out effect for truncated text */}
              <div className='absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-background to-transparent' />
            </div>
          </div>
        </Card>
      </motion.div>
    </Link>
  );
}
