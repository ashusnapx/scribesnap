"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Check,
  Copy,
  FileText,
  ArrowLeft,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Note, ParseResponse } from "@/lib/types";
import { copyToClipboard } from "@/lib/utils";

interface ParseResultProps {
  data: ParseResponse;
  onReset: () => void;
}

export function ParseResult({ data, onReset }: ParseResultProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await copyToClipboard(data.parsed_text);
      setCopied(true);
      toast.success("Text copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy text");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className='w-full max-w-4xl mx-auto space-y-8'
    >
      {/* Success Banner */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className='flex items-center justify-between bg-green-500/10 text-green-600 dark:text-green-400 p-4 rounded-xl border border-green-500/20'
      >
        <div className='flex items-center gap-3'>
          <div className='p-2 bg-green-500/20 rounded-full'>
            <Sparkles className='w-5 h-5' />
          </div>
          <span className='font-medium'>Note parsed successfully!</span>
        </div>
        <div className='flex gap-2'>
          <Button
            variant='ghost'
            size='sm'
            onClick={onReset}
            className='hover:bg-green-500/20'
          >
            <RefreshCw className='w-4 h-4 mr-2' />
            New Scan
          </Button>
        </div>
      </motion.div>

      <div className='grid md:grid-cols-2 gap-8 h-[600px]'>
        {/* Left: Original Image */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className='h-full flex flex-col'
        >
          <div className='flex items-center gap-2 mb-4 text-muted-foreground font-medium'>
            <FileText className='w-4 h-4' />
            <span>Original Note</span>
          </div>
          <Card className='flex-1 overflow-hidden bg-muted/30 border-muted p-2 flex items-center justify-center relative group'>
            <div className='absolute inset-0 bg-pattern opacity-5' />
            <img
              src={data.note.image_url}
              alt='Original handwritten note'
              className='max-w-full max-h-full object-contain rounded-lg shadow-sm transition-transform duration-500 group-hover:scale-[1.02]'
            />
          </Card>
        </motion.div>

        {/* Right: Extracted Text */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className='h-full flex flex-col'
        >
          <div className='flex items-center justify-between mb-4'>
            <div className='flex items-center gap-2 text-muted-foreground font-medium'>
              <Sparkles className='w-4 h-4 text-primary' />
              <span>Extracted Text</span>
            </div>
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

          <Card className='flex-1 relative group overflow-hidden border-primary/20 bg-background/50 backdrop-blur-sm'>
            <textarea
              readOnly
              className='w-full h-full p-6 resize-none bg-transparent border-none outline-none font-mono text-sm leading-relaxed text-foreground/90 selection:bg-primary/20'
              value={data.parsed_text}
            />
            {/* Fade effect at bottom */}
            <div className='absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-background to-transparent pointer-events-none' />
          </Card>
        </motion.div>
      </div>
    </motion.div>
  );
}
