"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { Sparkles, History, Settings, PenTool } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { CommandPalette } from "./CommandPalette";

export function Navbar() {
  const pathname = usePathname();
  const { scrollY } = useScroll();
  const [hidden, setHidden] = React.useState(false);
  const [scrolled, setScrolled] = React.useState(false);

  // Hide navbar on scroll down, show on scroll up
  useMotionValueEvent(scrollY, "change", (latest) => {
    const previous = scrollY.getPrevious() ?? 0;
    if (latest > previous && latest > 150) {
      setHidden(true);
    } else {
      setHidden(false);
    }
    setScrolled(latest > 20);
  });

  const navItems = [
    { href: "/", label: "New Scan", icon: PenTool },
    { href: "/history", label: "History", icon: History },
  ];

  return (
    <motion.header
      variants={{
        visible: { y: 0 },
        hidden: { y: "-100%" },
      }}
      animate={hidden ? "hidden" : "visible"}
      transition={{ duration: 0.35, ease: "easeInOut" }}
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled ?
          "bg-white/80 dark:bg-black/80 backdrop-blur-md border-b border-border/50"
        : "bg-transparent border-transparent",
      )}
    >
      <div className='container mx-auto px-4 h-16 flex items-center justify-between'>
        {/* Logo */}
        <Link href='/' className='flex items-center gap-2 group'>
          <div className='bg-primary text-primary-foreground p-1.5 rounded-lg group-hover:scale-105 transition-transform duration-300'>
            <Sparkles className='w-5 h-5' />
          </div>
          <span className='font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70'>
            ScribeSnap
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className='hidden md:flex items-center gap-1 absolute left-1/2 -translate-x-1/2'>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant='ghost'
                  size='sm'
                  className={cn(
                    "gap-2 rounded-full px-4 transition-all duration-300",
                    isActive ?
                      "bg-muted font-medium text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                  )}
                >
                  <item.icon className='w-4 h-4' />
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </nav>

        {/* Right Actions */}
        <div className='flex items-center gap-2'>
          <CommandPalette />
        </div>
      </div>
    </motion.header>
  );
}
