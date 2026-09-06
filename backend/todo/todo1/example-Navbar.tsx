/* =====================================================================
   EXAMPLE Navbar — shows how to use the nav-underline utility +
   the framer-motion variants together.
   Drop into src/components/site/Navbar.tsx
   ===================================================================== */

"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plane, Menu, X } from "lucide-react";
import { logoHover, mobileMenuVariants, heroFadeUp } from "./joby-motion";

const NAV_LINKS = [
  { label: "Experience", href: "#experience" },
  { label: "Routes", href: "#routes" },
  { label: "How it works", href: "#how" },
  { label: "Fleet", href: "#fleet" },
  { label: "Stories", href: "#news" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.65, 0, 0.35, 1] }}
      className={`fixed top-0 inset-x-0 z-40 transition-all duration-500
        ${scrolled ? "bg-cream/90 backdrop-blur-md border-b border-ink/10" : "bg-transparent"}`}
    >
      <nav className="max-w-7xl mx-auto px-6 lg:px-8 h-16 md:h-20 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="flex items-center gap-2">
          <motion.div
            {...logoHover}
            className="w-8 h-8 rounded-full bg-ink text-cream flex items-center justify-center"
          >
            <Plane className="w-4 h-4 -rotate-45" />
          </motion.div>
          <span className="font-display text-xl font-semibold tracking-tight">Skyway</span>
        </a>

        {/* Desktop nav — uses nav-underline utility (no framer-motion for hover) */}
        <div className="hidden md:flex items-center gap-10">
          {NAV_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="nav-underline text-sm font-medium text-ink/80 hover:text-ink transition-colors duration-300"
            >
              {l.label}
            </a>
          ))}
        </div>

        {/* Right side */}
        <div className="hidden md:flex items-center gap-3">
          <a href="#" className="nav-underline text-sm font-medium text-ink/80 hover:text-ink">
            Sign in
          </a>
          <button className="px-5 py-2.5 rounded-full bg-ink text-cream text-sm font-medium hover:bg-sky transition-all duration-500">
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

      {/* Mobile menu — uses mobileMenuVariants */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            variants={mobileMenuVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="md:hidden bg-cream border-b border-ink/10 overflow-hidden"
          >
            <div className="px-6 py-4 flex flex-col gap-1">
              {NAV_LINKS.map((l) => (
                <a
                  key={l.label}
                  href={l.href}
                  onClick={() => setMobileOpen(false)}
                  className="text-left py-3 text-base font-medium text-ink/80 border-b border-ink/5"
                >
                  {l.label}
                </a>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
