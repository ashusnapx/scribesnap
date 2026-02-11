import type { Metadata } from "next";
// import { Inter } from "next/font/google"; // Using custom Apple-system fonts instead
import "./globals.css";
import { Providers } from "./providers";
import { Navbar } from "@/components/layout/Navbar";
import { Toaster } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

// const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ScribeSnap - AI Handwritten Note Parser",
  description:
    "Convert your handwritten notes into digital text instantly with AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased selection:bg-primary/20",
          // inter.className
        )}
      >
        <Providers>
          <div className='relative flex min-h-screen flex-col'>
            <Navbar />
            <main className='flex-1 pt-16'>{children}</main>
          </div>
          <Toaster richColors position='top-center' closeButton />
        </Providers>
      </body>
    </html>
  );
}
