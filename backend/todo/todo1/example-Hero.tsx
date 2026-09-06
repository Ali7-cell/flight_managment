/* =====================================================================
   EXAMPLE Hero — shows how to combine:
   - scroll-linked plane motion (usePlaneScroll)
   - scroll-linked contrail (useContrailScroll)
   - scroll-linked clouds parallax (useCloudsScroll)
   - scroll-linked hero text parallax + fade (useHeroTextScroll)
   - scroll-linked search form lift (useSearchFormScroll)
   - scroll-linked section scale (useHeroSectionScroll)
   - scroll-linked hint fade (useScrollHintScroll)
   - the rotating headline (AnimatePresence + headlineSwap variant)
   - the planeFloat gentle bobbing (layered on top of scroll motion)
   - CSS cloud drift (animate-drift-1/2/3 from joby-animations.css)
   Drop into src/components/site/Hero.tsx
   ===================================================================== */

"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence, useScroll } from "framer-motion";
import { ArrowDown, Plane, Sparkles } from "lucide-react";
import {
  headlineSwap,
  planeFloat,
  usePlaneScroll,
  useContrailScroll,
  useCloudsScroll,
  useHeroTextScroll,
  useSearchFormScroll,
  useHeroSectionScroll,
  useScrollHintScroll,
} from "./joby-motion";

const SLIDES = [
  "Skip traffic. Time to fly.",
  "Skip the lines. Time to fly.",
  "Skip the wait. Time to fly.",
  "Skip the noise. Time to fly.",
];

export function Hero() {
  const [slideIdx, setSlideIdx] = useState(0);
  const heroRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const t = setInterval(() => {
      setSlideIdx((i) => (i + 1) % SLIDES.length);
    }, 3800);
    return () => clearInterval(t);
  }, []);

  // Scroll progress through the hero (0 → 1 as the hero scrolls out of view)
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });

  // ---- Scroll-linked transforms (Joby feel) ----
  const sectionMotion = useHeroSectionScroll(scrollYProgress);
  const planeMotion = usePlaneScroll(scrollYProgress);
  const contrailMotion = useContrailScroll(scrollYProgress);
  const cloudsMotion = useCloudsScroll(scrollYProgress);
  const textMotion = useHeroTextScroll(scrollYProgress);
  const searchMotion = useSearchFormScroll(scrollYProgress);
  const hintMotion = useScrollHintScroll(scrollYProgress);

  return (
    <motion.section
      ref={heroRef}
      style={{ scale: sectionMotion.scale, y: sectionMotion.y }}
      className="relative min-h-[100svh] pt-16 md:pt-20 overflow-hidden bg-gradient-to-b from-sky via-sky to-deep-blue text-cream will-change-transform"
    >
      {/* Cloud layer — parallax background (slower than text) */}
      <motion.div
        style={{ y: cloudsMotion.y, opacity: cloudsMotion.opacity }}
        className="absolute inset-0 will-change-transform"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-[#7CC0F5] via-sky to-deep-blue" />
        {/* CSS-driven cloud drift (different speeds per blob) */}
        <div className="absolute top-[12%] left-[10%] w-72 h-32 rounded-full bg-cream/30 blur-3xl animate-drift-1" />
        <div className="absolute top-[28%] right-[8%] w-96 h-40 rounded-full bg-cream/20 blur-3xl animate-drift-2" />
        <div className="absolute top-[45%] left-[20%] w-80 h-32 rounded-full bg-cream/15 blur-3xl animate-drift-3" />
        {/* Sun glow */}
        <div className="absolute top-[8%] right-[12%] w-44 h-44 rounded-full bg-cream/60 blur-2xl" />
      </motion.div>

      {/* Plane — scroll-linked: flies DOWN-RIGHT as user scrolls */}
      <motion.div
        initial={{ x: -120, y: 30, opacity: 0 }}
        animate={{ x: 0, y: 0, opacity: 1 }}
        transition={{ duration: 1.4, ease: [0.65, 0, 0.35, 1], delay: 0.4 }}
        className="absolute top-[18%] left-1/2 -translate-x-1/2 hidden md:block z-[5] will-change-transform"
      >
        <motion.div
          style={{
            x: planeMotion.x,
            y: planeMotion.y,
            rotate: planeMotion.rotate,
            opacity: planeMotion.opacity,
          }}
          className="relative will-change-transform"
        >
          {/* Gentle bobbing layered on top of the scroll-driven motion */}
          <motion.div {...planeFloat}>
            <Plane className="w-14 h-14 text-cream/80" />
          </motion.div>

          {/* Contrail grows + fades with scroll */}
          <motion.div
            style={{ scaleX: contrailMotion.scaleX, opacity: contrailMotion.opacity }}
            className="absolute right-full top-1/2 -translate-y-1/2 h-[2px] w-64 bg-gradient-to-l from-cream/80 to-transparent origin-right will-change-transform"
          />
        </motion.div>
      </motion.div>

      {/* Text content — parallax up + fade out */}
      <motion.div
        style={{ y: textMotion.y, opacity: textMotion.opacity }}
        className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 pt-12 md:pt-24 pb-8 will-change-transform"
      >
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.65, 0, 0.35, 1], delay: 0.1 }}
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
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.65, 0, 0.35, 1], delay: 0.3 }}
          className="mt-6 max-w-xl text-cream/80 text-lg md:text-xl font-light"
        >
          A new altitude of travel. Search the world&apos;s routes, pick your seat,
          and board in minutes — all from a single, beautifully simple search.
        </motion.p>
      </motion.div>

      {/* Search form — lifts away with stronger parallax */}
      <motion.div
        style={{ y: searchMotion.y, opacity: searchMotion.opacity }}
        className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 pb-12 md:pb-20 will-change-transform"
      >
        {/* <SearchForm /> — drop your search component here */}
        <div className="h-32 rounded-3xl bg-cream/10 border border-cream/20 flex items-center justify-center text-cream/60">
          Search form goes here
        </div>

        {/* Scroll hint — fades out immediately on scroll */}
        <motion.button
          style={{ opacity: hintMotion.opacity }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="mt-10 mx-auto md:mx-0 flex items-center gap-2 text-cream/70 hover:text-cream transition-colors text-sm will-change-transform"
        >
          <span>Scroll to explore</span>
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          >
            <ArrowDown className="w-4 h-4" />
          </motion.div>
        </motion.button>
      </motion.div>
    </motion.section>
  );
}
