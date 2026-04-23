import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HOS daily log",
  description: "Driver daily log and hours of service recap (assessment app)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-zinc-200 bg-white/80 px-4 py-3 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
          <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 text-sm">
            <a className="font-medium text-zinc-900 dark:text-zinc-100" href="/">
              Home
            </a>
            <a className="text-sky-700 dark:text-sky-400" href="/daily-log">
              Daily log
            </a>
            <a className="text-sky-700 dark:text-sky-400" href="/hos">
              HOS reference
            </a>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
