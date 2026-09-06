"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowDown, Plane, Sparkles } from "lucide-react";
import { SearchForm } from "./SearchForm";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

// Rotating hero text slides (Joby-style)
const SLIDES = [
  "Skip traffic. Time to fly.",
  "Skip the lines. Time to fly.",
  "Skip the wait. Time to fly.",
  "Skip the noise. Time to fly.",
];

export function Hero() {
  const [slideIdx, setSlideIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setSlideIdx((i) => (i + 1) % SLIDES.length);
    }, 3800);
    return () => clearInterval(t);
  }, []);

  return (
    <section className="relative min-h-[100svh] pt-16 md:pt-20 overflow-hidden bg-gradient-to-b from-sky via-sky to-deep-blue text-cream">
      {/* Soft sky gradient + clouds */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-b from-[#7CC0F5] via-sky to-deep-blue" />
        {/* Soft cloud blobs */}
        <motion.div
          animate={{ x: [0, 40, 0], y: [0, -10, 0] }}
          transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-[12%] left-[10%] w-72 h-32 rounded-full bg-cream/30 blur-3xl"
        />
        <motion.div
          animate={{ x: [0, -60, 0], y: [0, 20, 0] }}
          transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-[28%] right-[8%] w-96 h-40 rounded-full bg-cream/20 blur-3xl"
        />
        <motion.div
          animate={{ x: [0, 30, 0], y: [0, -15, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-[45%] left-[20%] w-80 h-32 rounded-full bg-cream/15 blur-3xl"
        />
        {/* Sun glow */}
        <div className="absolute top-[8%] right-[12%] w-44 h-44 rounded-full bg-cream/60 blur-2xl" />
      </div>

      {/* Floating plane */}
      <motion.div
        initial={{ x: -120, y: 30, opacity: 0 }}
        animate={{ x: 0, y: 0, opacity: 1 }}
        transition={{ duration: 1.4, ease: JOB_EASE, delay: 0.4 }}
        className="absolute top-[18%] left-1/2 -translate-x-1/2 hidden md:block"
      >
        <motion.div
          animate={{ y: [0, -8, 0], rotate: [-3, 2, -3] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        >
          <Plane className="w-14 h-14 text-cream/80 -rotate-45" />
        </motion.div>
        {/* Contrail */}
        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 1, delay: 1.4, ease: JOB_EASE }}
          className="absolute right-full top-1/2 -translate-y-1/2 h-[2px] w-64 bg-gradient-to-l from-cream/80 to-transparent origin-right"
        />
      </motion.div>

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 pt-12 md:pt-24 pb-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: JOB_EASE, delay: 0.1 }}
          className="flex items-center gap-2 mb-6 md:mb-10"
        >
          <Sparkles className="w-4 h-4" />
          <span className="text-xs font-semibold uppercase tracking-widest text-cream/80">
            Now boarding · Skyway Air
          </span>
        </motion.div>

        {/* Animated headline */}
        <h1 className="font-display font-semibold tracking-tight text-cream leading-[0.92] text-[clamp(2.5rem,7vw,5.5rem)] max-w-5xl">
          <AnimatePresence mode="wait">
            <motion.span
              key={slideIdx}
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -24 }}
              transition={{ duration: 0.6, ease: JOB_EASE }}
              className="block"
            >
              {SLIDES[slideIdx]}
            </motion.span>
          </AnimatePresence>
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: JOB_EASE, delay: 0.3 }}
          className="mt-6 max-w-xl text-cream/80 text-lg md:text-xl font-light"
        >
          A new altitude of travel. Search the world&apos;s routes, pick your seat,
          and board in minutes — all from a single, beautifully simple search.
        </motion.p>
      </div>

      {/* Search form anchored bottom */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 pb-12 md:pb-20">
        <SearchForm />

        {/* Stats strip */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: JOB_EASE, delay: 0.5 }}
          className="mt-6 md:mt-8 grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-8 text-cream"
        >
          {[
            { value: "540", label: "Daily flights" },
            { value: "21", label: "Global destinations" },
            { value: "99%", label: "On-time arrival" },
            { value: "4.9", label: "Avg. rating" },
          ].map((s) => (
            <div key={s.label} className="border-l border-cream/30 pl-3">
              <div className="font-display text-2xl md:text-3xl font-semibold">{s.value}</div>
              <div className="text-xs md:text-sm text-cream/70 mt-1">{s.label}</div>
            </div>
          ))}
        </motion.div>

        {/* Scroll hint */}
        <motion.button
          onClick={() => document.getElementById("routes")?.scrollIntoView({ behavior: "smooth" })}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="mt-10 mx-auto md:mx-0 flex items-center gap-2 text-cream/70 hover:text-cream transition-colors text-sm"
        >
          <span>Explore routes</span>
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          >
            <ArrowDown className="w-4 h-4" />
          </motion.div>
        </motion.button>
      </div>
    </section>
  );
}
