"use client";

import Link from "next/link";
import { Sparkles, Github, Heart, PenTool, History } from "lucide-react";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className='relative border-t border-border/40 bg-background/50 backdrop-blur-sm'>
      {/* Subtle gradient line at top */}
      <div className='absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent' />

      <div className='container mx-auto px-4 py-12'>
        <div className='grid grid-cols-1 md:grid-cols-3 gap-10'>
          {/* Brand */}
          <div className='space-y-4'>
            <Link href='/' className='flex items-center gap-2 group w-fit'>
              <div className='bg-primary text-primary-foreground p-1.5 rounded-lg group-hover:scale-105 transition-transform duration-300'>
                <Sparkles className='w-5 h-5' />
              </div>
              <span className='font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70'>
                ScribeSnap
              </span>
            </Link>
            <p className='text-sm text-muted-foreground leading-relaxed max-w-xs'>
              AI-powered handwritten note parser. Convert your handwritten notes
              into digital text instantly with Google Gemini Vision.
            </p>
          </div>

          {/* Quick Links */}
          <div className='space-y-4'>
            <h3 className='text-sm font-semibold tracking-wider uppercase text-muted-foreground/70'>
              Navigate
            </h3>
            <nav className='flex flex-col gap-2.5'>
              <Link
                href='/'
                className='text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 flex items-center gap-2 group w-fit'
              >
                <PenTool className='w-3.5 h-3.5 group-hover:text-primary transition-colors' />
                New Scan
              </Link>
              <Link
                href='/history'
                className='text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 flex items-center gap-2 group w-fit'
              >
                <History className='w-3.5 h-3.5 group-hover:text-primary transition-colors' />
                History
              </Link>
            </nav>
          </div>

          {/* Tech Stack */}
          <div className='space-y-4'>
            <h3 className='text-sm font-semibold tracking-wider uppercase text-muted-foreground/70'>
              Built With
            </h3>
            <div className='flex flex-wrap gap-2'>
              {[
                "Next.js",
                "FastAPI",
                "PostgreSQL",
                "Gemini AI",
                "Docker",
                "Tailwind",
              ].map((tech) => (
                <span
                  key={tech}
                  className='text-xs px-2.5 py-1 rounded-full bg-muted/60 text-muted-foreground border border-border/50 hover:bg-muted hover:text-foreground transition-colors duration-200 cursor-default'
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className='mt-10 pt-6 border-t border-border/30 flex flex-col sm:flex-row items-center justify-between gap-4'>
          <p className='text-xs text-muted-foreground/60'>
            © {currentYear} ScribeSnap. Crafted with precision.
          </p>
          <div className='flex items-center gap-1 text-xs text-muted-foreground/60'>
            <span>Made with</span>
            <Heart className='w-3 h-3 text-red-400 fill-red-400 animate-pulse' />
            <span>by</span>
            <a
              href='https://github.com/ashusnapx'
              target='_blank'
              rel='noopener noreferrer'
              className='font-medium text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1'
            >
              <Github className='w-3 h-3' />
              Ashutosh Kumar
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
