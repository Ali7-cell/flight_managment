"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plane, Menu, X } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";
import { cn } from "@/lib/utils";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const NAV_LINKS = [
  { label: "Experience", target: "experience" },
  { label: "Routes", target: "routes" },
  { label: "How it works", target: "how" },
  { label: "Fleet", target: "fleet" },
  { label: "Stories", target: "news" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { setStep, reset } = useBookingStore();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const scrollTo = (id: string) => {
    setMobileOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const scrollToTop = () => {
    setMobileOpen(false);
    reset();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: JOB_EASE }}
      className={cn(
        "fixed top-0 inset-x-0 z-40 transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]",
        scrolled
          ? "bg-cream/90 backdrop-blur-md border-b border-ink/10"
          : "bg-transparent"
      )}
    >
      <nav className="max-w-7xl mx-auto px-6 lg:px-8 h-16 md:h-20 flex items-center justify-between">
        {/* Logo */}
        <button onClick={scrollToTop} className="flex items-center gap-2 group">
          <motion.div
            whileHover={{ rotate: -8, scale: 1.05 }}
            transition={{ duration: 0.4, ease: JOB_EASE }}
            className="w-8 h-8 rounded-full bg-ink text-cream flex items-center justify-center"
          >
            <Plane className="w-4 h-4 -rotate-45" />
          </motion.div>
          <span className="text-xl font-display font-semibold tracking-tight">Skyway</span>
        </button>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-10">
          {NAV_LINKS.map((l) => (
            <button
              key={l.label}
              onClick={() => scrollTo(l.target)}
              className="nav-underline text-sm font-medium text-ink/80 hover:text-ink transition-colors duration-300 ease-[cubic-bezier(0.65,0,0.35,1)]"
            >
              {l.label}
            </button>
          ))}
        </div>

        {/* Right side */}
        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={() => {
              reset();
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            className="nav-underline text-sm font-medium text-ink/80 hover:text-ink transition-colors"
          >
            Sign in
          </button>
          <button
            onClick={scrollToTop}
            className="px-5 py-2.5 rounded-full bg-ink text-cream text-sm font-medium hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]"
          >
            Book a flight
          </button>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden w-10 h-10 flex items-center justify-center rounded-full bg-cream/80 border border-ink/10"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: JOB_EASE }}
            className="md:hidden bg-cream border-b border-ink/10 overflow-hidden"
          >
            <div className="px-6 py-4 flex flex-col gap-1">
              {NAV_LINKS.map((l) => (
                <button
                  key={l.label}
                  onClick={() => scrollTo(l.target)}
                  className="text-left py-3 text-base font-medium text-ink/80 border-b border-ink/5"
                >
                  {l.label}
                </button>
              ))}
              <button
                onClick={scrollToTop}
                className="mt-4 py-3 rounded-full bg-ink text-cream font-medium"
              >
                Book a flight
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
