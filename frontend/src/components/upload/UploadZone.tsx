"use client";

import * as React from "react";
import { useDropzone, DropzoneOptions } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  UploadCloud,
  FileImage,
  X,
  AlertCircle,
  Loader2,
  Sparkles,
  Plus,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useParseNote } from "@/hooks/useParseNote";
import { Progress } from "@/components/ui/progress"; // Need to add progress component

// State machine for upload process
type UploadState =
  | "idle"
  | "dragging"
  | "preview"
  | "uploading"
  | "success"
  | "error";

interface UploadZoneProps {
  onParseComplete: (data: any) => void;
}

export function UploadZone({ onParseComplete }: UploadZoneProps) {
  const [file, setFile] = React.useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const [progress, setProgress] = React.useState(0);

  // Custom mutation hook for API call
  const {
    mutate: parseNote,
    isPending,
    error,
  } = useParseNote({
    onSuccess: (data) => {
      setProgress(100);
      toast.success("Note parsed successfully!");
      // Short delay to show 100% progress before transition
      setTimeout(() => onParseComplete(data), 500);
    },
    onError: (err) => {
      setProgress(0);
      toast.error(err.message || "Failed to parse note");
    },
  });

  // Cleanup preview URL on unmount
  React.useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // Drag and drop configuration
  const onDrop = React.useCallback((acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: {
        "image/jpeg": [],
        "image/png": [],
        "image/jpg": [],
      },
      maxSize: 10 * 1024 * 1024, // 10MB
      multiple: false,
      disabled: isPending,
    });

  const handleRemoveFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setProgress(0);
  };

  const handleUpload = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!file) return;
    parseNote(file);

    // Fake progress for improved UX (since actual upload progress isn't available via fetch)
    // 90% is max until actual completion
    let p = 0;
    const interval = setInterval(() => {
      p += Math.random() * 10;
      if (p > 90) {
        clearInterval(interval);
        p = 90;
      }
      setProgress(p);
    }, 200);
  };

  // Determine current UI state
  const state: UploadState =
    isPending ? "uploading"
    : error ? "error"
    : file ? "preview"
    : isDragActive ? "dragging"
    : "idle";

  return (
    <div className='w-full max-w-2xl mx-auto'>
      <motion.div
        layout
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div
          {...getRootProps()}
          className={cn(
            "relative group cursor-pointer overflow-hidden rounded-3xl border-2 border-dashed transition-all duration-300 ease-in-out min-h-[400px] flex flex-col items-center justify-center p-8",
            isDragActive ?
              "border-primary bg-primary/5 scale-[1.02]"
            : "border-border hover:border-primary/50 hover:bg-muted/30",
            state === "preview" &&
              "border-solid border-border/50 bg-background",
            isDragReject && "border-destructive bg-destructive/5",
          )}
        >
          <input {...getInputProps()} />

          <AnimatePresence mode='wait'>
            {state === "idle" && (
              <motion.div
                key='idle'
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className='text-center space-y-4 max-w-md pointer-events-none'
              >
                <div className='w-20 h-20 bg-muted/50 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300'>
                  <UploadCloud className='w-10 h-10 text-muted-foreground group-hover:text-primary transition-colors' />
                </div>
                <h3 className='text-2xl font-semibold tracking-tight'>
                  Drop your note here
                </h3>
                <p className='text-muted-foreground text-lg'>
                  Drag & drop or click to select a handwritten note.
                  <br />
                  <span className='text-sm opacity-70'>
                    Supports JPG, PNG up to 10MB
                  </span>
                </p>
                <div className='pt-4'>
                  <Button
                    variant='outline'
                    className='rounded-full px-6 pointer-events-auto'
                  >
                    Select File
                  </Button>
                </div>
              </motion.div>
            )}

            {state === "dragging" && (
              <motion.div
                key='dragging'
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className='absolute inset-0 z-10 flex items-center justify-center bg-primary/5 backdrop-blur-sm'
              >
                <div className='text-center'>
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                  >
                    <Plus className='w-16 h-16 text-primary mx-auto mb-4' />
                  </motion.div>
                  <p className='text-xl font-medium text-primary'>
                    Drop to upload
                  </p>
                </div>
              </motion.div>
            )}

            {(state === "preview" || state === "uploading") &&
              file &&
              previewUrl && (
                <motion.div
                  key='preview'
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className='w-full h-full flex flex-col items-center cursor-default'
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* Image Preview Card */}
                  <div className='relative w-full aspect-[4/3] max-h-[300px] mb-8 rounded-2xl overflow-hidden shadow-lg group-hover:shadow-xl transition-shadow bg-muted'>
                    <img
                      src={previewUrl}
                      alt='Preview'
                      className='w-full h-full object-contain'
                    />

                    {/* Remove Button */}
                    {!isPending && (
                      <Button
                        variant='destructive'
                        size='icon'
                        className='absolute top-2 right-2 rounded-full h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm'
                        onClick={handleRemoveFile}
                      >
                        <X className='w-4 h-4' />
                      </Button>
                    )}

                    {/* Loading Overlay */}
                    {isPending && (
                      <div className='absolute inset-0 bg-background/60 backdrop-blur-sm flex items-center justify-center flex-col gap-3'>
                        <div className='bg-background rounded-full p-4 shadow-lg'>
                          <Loader2 className='w-8 h-8 text-primary animate-spin' />
                        </div>
                        <p className='font-medium text-sm animate-pulse'>
                          Analyzing handwriting...
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Actions or Progress */}
                  <div className='w-full max-w-xs space-y-4'>
                    {isPending ?
                      <div className='space-y-2'>
                        {/* Assuming Progress component is available, if not need to add it */}
                        <div className='h-2 w-full bg-muted rounded-full overflow-hidden'>
                          <motion.div
                            className='h-full bg-primary'
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                          />
                        </div>
                        <p className='text-xs text-center text-muted-foreground'>
                          This may take a few seconds
                        </p>
                      </div>
                    : <Button
                        size='lg'
                        className='w-full rounded-full gap-2 shadow-lg hover:shadow-primary/25 transition-all text-lg h-12'
                        onClick={handleUpload}
                      >
                        <Sparkles className='w-5 h-5' />
                        Parse Note
                      </Button>
                    }
                  </div>
                </motion.div>
              )}

            {state === "error" && (
              <motion.div
                key='error'
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className='text-center space-y-4'
              >
                <div className='w-16 h-16 bg-destructive/10 text-destructive rounded-full flex items-center justify-center mx-auto'>
                  <AlertCircle className='w-8 h-8' />
                </div>
                <h3 className='text-lg font-semibold text-destructive'>
                  Upload Failed
                </h3>
                <p className='text-muted-foreground'>
                  {error?.message || "Something went wrong"}
                </p>
                <Button
                  variant='outline'
                  onClick={handleRemoveFile}
                  className='mt-4'
                >
                  Try Again
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
