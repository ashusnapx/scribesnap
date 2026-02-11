"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Calculator,
  Calendar,
  CreditCard,
  Settings,
  Smile,
  User,
  Search,
  PenTool,
  History,
  Laptop,
  Moon,
  Sun,
  Laptop2,
} from "lucide-react";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";

export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const router = useRouter();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = React.useCallback((command: () => unknown) => {
    setOpen(false);
    command();
  }, []);

  return (
    <>
      <Button
        variant='outline'
        size='sm'
        className='text-muted-foreground text-xs gap-2 px-3 h-9 hidden md:flex rounded-full bg-muted/30 border-muted-foreground/20 hover:bg-muted/50 hover:text-foreground transition-all ml-auto'
        onClick={() => setOpen(true)}
      >
        <Search className='w-3.5 h-3.5' />
        <span className='inline-block'>Search...</span>
        <kbd className='pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100'>
          <span className='text-xs'>⌘</span>K
        </kbd>
      </Button>

      {/* Mobile Trigger */}
      <Button
        variant='ghost'
        size='icon'
        className='md:hidden rounded-full'
        onClick={() => setOpen(true)}
      >
        <Search className='w-5 h-5' />
      </Button>

      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput placeholder='Type a command or search...' />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>

          <CommandGroup heading='Navigation'>
            <CommandItem onSelect={() => runCommand(() => router.push("/"))}>
              <PenTool className='mr-2 h-4 w-4' />
              <span>New Scan</span>
              <CommandShortcut>⌘N</CommandShortcut>
            </CommandItem>
            <CommandItem
              onSelect={() => runCommand(() => router.push("/history"))}
            >
              <History className='mr-2 h-4 w-4' />
              <span>History</span>
              <CommandShortcut>⌘H</CommandShortcut>
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading='Theme'>
            <CommandItem
              onSelect={() =>
                runCommand(() =>
                  document.documentElement.classList.remove("dark"),
                )
              }
            >
              <Sun className='mr-2 h-4 w-4' />
              <span>Light</span>
            </CommandItem>
            <CommandItem
              onSelect={() =>
                runCommand(() => document.documentElement.classList.add("dark"))
              }
            >
              <Moon className='mr-2 h-4 w-4' />
              <span>Dark</span>
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading='System'>
            <CommandItem
              onSelect={() =>
                runCommand(() => window.open("/api/health", "_blank"))
              }
            >
              <Laptop2 className='mr-2 h-4 w-4' />
              <span>System Health</span>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
