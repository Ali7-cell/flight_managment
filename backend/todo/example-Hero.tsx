/* =====================================================================
   EXAMPLE Hero — shows how to combine:
   - the cloud drift animations (CSS classes from joby-animations.css)
   - the heroFadeUp variant from joby-motion.ts
   - the headlineSwap variant (AnimatePresence mode="wait") for rotating headline
   - the planeFloat loop
   - the scrollHint chevron bounce
   Drop into src/components/site/Hero.tsx
   ===================================================================== */

"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowDown, Plane, Sparkles } from "lucide-react";
import { heroFadeUp, headlineSwap, planeFloat, scrollHint } from "./joby-motion";

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
      {/* Cloud layer — uses .animate-drift-1/2/3 from joby-animations.css */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-b from-[#7CC0F5] via-sky to-deep-blue" />
        <div className="absolute top-[12%] left-[10%] w-72 h-32 rounded-full bg-cream/30 blur-3xl animate-drift-1" />
        <div className="absolute top-[28%] right-[8%] w-96 h-40 rounded-full bg-cream/20 blur-3xl animate-drift-2" />
        <div className="absolute top-[45%] left-[20%] w-80 h-32 rounded-full bg-cream/15 blur-3xl animate-drift-3" />
        <div className="absolute top-[8%] right-[12%] w-44 h-44 rounded-full bg-cream/60 blur-2xl" />
      </div>

      {/* Floating plane — uses planeFloat from joby-motion.ts */}
      <motion.div
        initial={{ x: -120, y: 30, opacity: 0 }}
        animate={{ x: 0, y: 0, opacity: 1 }}
        transition={{ duration: 1.4, ease: [0.65, 0, 0.35, 1], delay: 0.4 }}
        className="absolute top-[18%] left-1/2 -translate-x-1/2 hidden md:block"
      >
        <motion.div {...planeFloat}>
          <Plane className="w-14 h-14 text-cream/80 -rotate-45" />
        </motion.div>
      </motion.div>

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 pt-12 md:pt-24 pb-8">
        <motion.div
          variants={heroFadeUp}
          initial="hidden"
          animate="visible"
          className="flex items-center gap-2 mb-6 md:mb-10"
        >
          <Sparkles className="w-4 h-4" />
          <span className="font-eyebrow text-cream/80">Now boarding · Skyway Air</span>
        </motion.div>

        {/* Rotating headline — AnimatePresence + headlineSwap */}
        <h1 className="font-display font-semibold tracking-tight text-cream leading-[0.92] text-[clamp(2.5rem,7vw,5.5rem)] max-w-5xl">
          <AnimatePresence mode="wait">
            <motion.span
              key={slideIdx}
              variants={headlineSwap}
              initial="initial"
              animate="animate"
              exit="exit"
              className="block"
            >
              {SLIDES[slideIdx]}
            </motion.span>
          </AnimatePresence>
        </h1>

        <motion.p
          variants={heroFadeUp}
          initial="hidden"
          animate="visible"
          transition={{ delay: 0.3 }}
          className="mt-6 max-w-xl text-cream/80 text-lg md:text-xl font-light"
        >
          A new altitude of travel. Search the world's routes, pick your seat,
          and board in minutes — all from a single, beautifully simple search.
        </motion.p>
      </div>

      {/* Scroll hint */}
      <motion.button
        {...scrollHint}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-2 text-cream/70 text-sm"
      >
        <span>Explore routes</span>
        <ArrowDown className="w-4 h-4" />
      </motion.button>
    </section>
  );
}
