"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { FileSearch } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className='flex flex-col items-center justify-center py-20 px-4 text-center max-w-md mx-auto'
    >
      <div className='w-24 h-24 bg-muted/50 rounded-full flex items-center justify-center mb-6 ring-8 ring-muted/20'>
        <FileSearch className='w-10 h-10 text-muted-foreground' />
      </div>

      <h3 className='text-2xl font-bold tracking-tight mb-2'>No notes found</h3>
      <p className='text-muted-foreground mb-8 text-balance'>
        You haven't scanned any notes yet. Upload your first handwritten note to
        get started.
      </p>

      <Link href='/'>
        <Button
          size='lg'
          className='rounded-full px-8 shadow-lg hover:shadow-primary/25'
        >
          Scan New Note
        </Button>
      </Link>
    </motion.div>
  );
}
