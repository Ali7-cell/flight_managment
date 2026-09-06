import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  weight: ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Skyway — Skip Traffic. Time to Fly.",
  description:
    "Skyway is a next-generation flight booking experience. Search routes, pick your seat, and board with confidence. Built with an electric aesthetic inspired by Joby Aviation.",
  keywords: [
    "flight booking",
    "airline tickets",
    "cheap flights",
    "air travel",
    "Skyway",
    "book a flight",
  ],
  authors: [{ name: "Skyway" }],
  openGraph: {
    title: "Skyway — Skip Traffic. Time to Fly.",
    description:
      "A next-generation flight booking experience with electric design language.",
    siteName: "Skyway",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Skyway — Skip Traffic. Time to Fly.",
    description: "A next-generation flight booking experience.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
