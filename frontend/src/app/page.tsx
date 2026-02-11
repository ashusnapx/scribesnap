"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { UploadZone } from "@/components/upload/UploadZone";
import { ParseResult } from "@/components/upload/ParseResult";
import { ParseResponse } from "@/lib/types";

export default function HomePage() {
  const [result, setResult] = React.useState<ParseResponse | null>(null);

  const handleReset = () => {
    setResult(null);
  };

  return (
    <div className='container mx-auto px-4 py-12 md:py-24 min-h-[80vh] flex flex-col items-center justify-center'>
      {/* Hero Content */}
      <motion.div
        layout
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className='text-center space-y-4 mb-12 max-w-2xl'
      >
        <span className='inline-block py-1 px-3 rounded-full bg-primary/10 text-primary text-sm font-medium mb-2'>
          AI-Powered Handwriting Recognition
        </span>
        <h1 className='text-4xl md:text-6xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/60'>
          Digitalize your notes <br /> in seconds.
        </h1>
        <p className='text-xl text-muted-foreground text-balance'>
          Upload any handwritten note and let our advanced AI extract every word
          with high precision.
        </p>
      </motion.div>

      {/* Main Interaction Zone */}
      <div className='w-full'>
        {!result ?
          <UploadZone onParseComplete={setResult} />
        : <ParseResult data={result} onReset={handleReset} />}
      </div>
    </div>
  );
}
