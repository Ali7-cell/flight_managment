/* =====================================================================
   JOBY AVIATION — FRAMER MOTION VARIANTS
   Drop-in TypeScript file. Import JOB_EASE and the variants you need.
   All easings match Joby's CSS cubic-bezier(0.65, 0, 0.35, 1).
   ===================================================================== */

import type { Variants, Transition, MotionValue } from "framer-motion";
import { useScroll, useTransform } from "framer-motion";

/* ---- The signature Joby easing curve (verbatim from their CSS) ---- */
export const JOB_EASE = [0.65, 0, 0.35, 1] as const;
export const JOB_EASE_OUT = [0.33, 1, 0.68, 1] as const;
export const JOB_EASE_IN = [0.35, 0.2, 0, 1] as const;

/* ---- Default durations (from Joby's CSS) ---- */
export const JOB_DURATIONS = {
  fast: 0.3,        // color / transform micro
  medium: 0.45,    // popover / dropdown
  slow: 0.5,       // hover lift, button state
  entrance: 0.6,   // scroll reveal
  long: 0.8,       // hero entrance
  extra: 0.9,      // large section reveal
} as const;

/* =====================================================================
   1. SCROLL REVEAL — use with `whileInView` + `viewport={{ once: true }}`
   ===================================================================== */

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: JOB_DURATIONS.entrance, ease: JOB_EASE },
  },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: JOB_DURATIONS.entrance, ease: JOB_EASE },
  },
};

export const fadeDown: Variants = {
  hidden: { opacity: 0, y: -24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: JOB_DURATIONS.entrance, ease: JOB_EASE },
  },
};

/* Large hero reveal (slower + larger offset) */
export const heroFadeUp: Variants = {
  hidden: { opacity: 0, y: 32 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: JOB_DURATIONS.long, ease: JOB_EASE },
  },
};

/* =====================================================================
   2. STAGGERED CONTAINERS — wrap lists of cards / nav items / etc.
   ===================================================================== */

export const staggerContainer = (
  stagger = 0.08,
  delayChildren = 0
): Variants => ({
  hidden: {},
  visible: {
    transition: {
      staggerChildren: stagger,
      delayChildren,
    },
  },
});

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: JOB_DURATIONS.entrance, ease: JOB_EASE },
  },
};

/* Larger stagger for big cards (featured routes, news) */
export const staggerItemLg: Variants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: JOB_EASE },
  },
};

/* =====================================================================
   3. HERO HEADLINE ROTATION — used with <AnimatePresence mode="wait">
   Joby's "translate-out-in-x" trick: slides right → fades → slides in from left.
   ===================================================================== */

export const headlineSwap: Variants = {
  initial: { opacity: 0, x: 24 },
  animate: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.6, ease: JOB_EASE },
  },
  exit: {
    opacity: 0,
    x: -24,
    transition: { duration: 0.6, ease: JOB_EASE },
  },
};

/* =====================================================================
   4. SLIDE IN — for dropdowns, popovers, mobile menu
   ===================================================================== */

export const slideInLeft: Variants = {
  hidden: { opacity: 0, x: -24 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: JOB_DURATIONS.medium, ease: JOB_EASE },
  },
  exit: {
    opacity: 0,
    x: -24,
    transition: { duration: JOB_DURATIONS.medium, ease: JOB_EASE },
  },
};

export const slideInRight: Variants = {
  hidden: { opacity: 0, x: 24 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: JOB_DURATIONS.medium, ease: JOB_EASE },
  },
  exit: {
    opacity: 0,
    x: 24,
    transition: { duration: JOB_DURATIONS.medium, ease: JOB_EASE },
  },
};

/* Dropdown / popover (appears from above the trigger) */
export const dropdownVariants: Variants = {
  hidden: { opacity: 0, y: -8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.25, ease: JOB_EASE },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: 0.25, ease: JOB_EASE },
  },
};

/* Mobile menu (expands from top) */
export const mobileMenuVariants: Variants = {
  hidden: { opacity: 0, height: 0 },
  visible: {
    opacity: 1,
    height: "auto",
    transition: { duration: 0.35, ease: JOB_EASE },
  },
  exit: {
    opacity: 0,
    height: 0,
    transition: { duration: 0.35, ease: JOB_EASE },
  },
};

/* =====================================================================
   5. BOOKING WIZARD STEP TRANSITION — between seats/passenger/payment
   ===================================================================== */

export const stepTransition: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: JOB_EASE },
  },
  exit: {
    opacity: 0,
    y: -24,
    transition: { duration: 0.45, ease: JOB_EASE },
  },
};

/* =====================================================================
   6. HOVER MICRO-INTERACTIONS
   ===================================================================== */

/* Card lift (for featured routes, news cards, flight cards) */
export const cardHover = {
  whileHover: {
    y: -6,
    transition: { duration: 0.5, ease: JOB_EASE },
  },
};

/* Button press feedback */
export const buttonTap = {
  whileTap: { scale: 0.97, transition: { duration: 0.15, ease: JOB_EASE } },
};

/* Logo wobble on hover (Navbar logo) */
export const logoHover = {
  whileHover: {
    rotate: -8,
    scale: 1.05,
    transition: { duration: 0.4, ease: JOB_EASE },
  },
};

/* =====================================================================
   7. DECORATIVE LOOPS — hero plane float, clouds, ken-burns
   ===================================================================== */

/* Hero plane gentle bobbing */
export const planeFloat = {
  animate: {
    y: [0, -8, 0],
    rotate: [-3, 2, -3],
    transition: {
      duration: 4,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

/* Cloud blob drift (use 3 instances with different durations) */
export const cloudDrift = (duration: number, delay = 0) => ({
  animate: {
    x: [0, 40, 0],
    y: [0, -10, 0],
    transition: {
      duration,
      repeat: Infinity,
      ease: "easeInOut" as const,
      delay,
    },
  },
});

/* Slow ken-burns zoom for hero image */
export const kenBurns = {
  initial: { scale: 1 },
  animate: {
    scale: [1, 1.08],
    transition: {
      duration: 20,
      ease: JOB_EASE_OUT as any,
      repeat: Infinity,
      repeatType: "reverse" as const,
    },
  },
};

/* Scroll-down chevron bounce */
export const scrollHint = {
  animate: {
    y: [0, 6, 0],
    transition: {
      duration: 1.4,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

/* =====================================================================
   8. LOADING STATES
   ===================================================================== */

/* Spinner rotation (for async buttons) */
export const spinner = {
  animate: {
    rotate: 360,
    transition: { duration: 1, repeat: Infinity, ease: "linear" },
  },
};

/* Loading dot pulse (for skeletons / placeholders) */
export const loadingPulse = {
  animate: {
    opacity: [0.4, 1, 0.4],
    transition: {
      duration: 1.6,
      repeat: Infinity,
      ease: "easeInOut" as const,
    },
  },
};

/* =====================================================================
   9. SEAT SELECTION — micro-interactions
   ===================================================================== */

/* Available seat hover (scale up slightly) */
export const seatHover = {
  whileHover: { scale: 1.05, transition: { duration: 0.2, ease: JOB_EASE } },
  whileTap: { scale: 0.95, transition: { duration: 0.2, ease: JOB_EASE } },
};

/* Selected seat pop-in (used when a seat becomes selected) */
export const seatSelected: Variants = {
  hidden: { scale: 1 },
  visible: {
    scale: 1.05,
    transition: { duration: 0.3, ease: JOB_EASE },
  },
};

/* =====================================================================
   10. CONFIRMATION — the "you're cleared" check
   ===================================================================== */

/* Check icon pop-in (used on booking confirmation) */
export const checkPop: Variants = {
  hidden: { scale: 0, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      duration: 0.6,
      ease: JOB_EASE,
      delay: 0.1,
    },
  },
};

/* Boarding pass reveal */
export const boardingPassReveal: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: JOB_EASE, delay: 0.2 },
  },
};

/* =====================================================================
   11. SHARED TRANSITION SHORTCUTS — for inline use
   ===================================================================== */

export const jobTransition: Transition = {
  duration: JOB_DURATIONS.entrance,
  ease: JOB_EASE,
};

export const jobTransitionFast: Transition = {
  duration: JOB_DURATIONS.fast,
  ease: JOB_EASE,
};

export const jobTransitionSlow: Transition = {
  duration: JOB_DURATIONS.slow,
  ease: JOB_EASE,
};

/* =====================================================================
   12. SCROLL-LINKED HERO MOTION (Joby feel)
   Use with framer-motion's `useScroll({ target: ref, offset: ["start start", "end start"] })`.
   These are factories — call them with the scrollYProgress MotionValue.
   ===================================================================== */

/**
 * Returns the scroll-linked transforms for the Hero plane.
 * The plane flies DOWN-RIGHT as the user scrolls, tilts up slightly,
 * and fades out near the end of the hero.
 *
 * Usage:
 *   const heroRef = useRef(null);
 *   const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
 *   const plane = usePlaneScroll(scrollYProgress);
 *   <motion.div style={{ x: plane.x, y: plane.y, rotate: plane.rotate, opacity: plane.opacity }}>...</motion.div>
 */
export function usePlaneScroll(progress: MotionValue<number>) {
  const x = useTransform(progress, [0, 1], [0, 600]);
  const y = useTransform(progress, [0, 1], [0, 380]);
  const rotate = useTransform(progress, [0, 1], [-45, -15]);
  const opacity = useTransform(progress, [0, 0.7, 1], [1, 0.8, 0]);
  return { x, y, rotate, opacity };
}

/**
 * Returns scroll-linked transforms for the contrail that follows the plane.
 * The contrail grows longer as the plane flies further, then fades.
 */
export function useContrailScroll(progress: MotionValue<number>) {
  const scaleX = useTransform(progress, [0, 1], [1, 2.4]);
  const opacity = useTransform(progress, [0, 0.6, 1], [0.8, 0.6, 0]);
  return { scaleX, opacity };
}

/**
 * Returns scroll-linked transforms for the parallax background layer (clouds).
 * Moves slower than the text so it feels "behind".
 */
export function useCloudsScroll(progress: MotionValue<number>) {
  const y = useTransform(progress, [0, 1], [0, -120]);
  const opacity = useTransform(progress, [0, 0.6, 1], [1, 0.7, 0]);
  return { y, opacity };
}

/**
 * Returns scroll-linked transforms for the hero text content.
 * Moves up faster than the section, fades out halfway through.
 */
export function useHeroTextScroll(progress: MotionValue<number>) {
  const y = useTransform(progress, [0, 1], [0, -180]);
  const opacity = useTransform(progress, [0, 0.5, 1], [1, 0.4, 0]);
  return { y, opacity };
}

/**
 * Returns scroll-linked transforms for the search form (lifts away first).
 */
export function useSearchFormScroll(progress: MotionValue<number>) {
  const y = useTransform(progress, [0, 1], [0, -220]);
  const opacity = useTransform(progress, [0, 0.4, 1], [1, 0.6, 0]);
  return { y, opacity };
}

/**
 * Returns scroll-linked transforms for the hero section itself (subtle scale + drift).
 */
export function useHeroSectionScroll(progress: MotionValue<number>) {
  const scale = useTransform(progress, [0, 1], [1, 1.05]);
  const y = useTransform(progress, [0, 1], [0, -60]);
  return { scale, y };
}

/**
 * Returns a fade-out for the scroll hint (fades out almost immediately).
 */
export function useScrollHintScroll(progress: MotionValue<number>) {
  const opacity = useTransform(progress, [0, 0.15], [1, 0]);
  return { opacity };
}

/* =====================================================================
   13. COUNT-UP HELPER (for stats)
   Usage: see example component below — this isn't a Framer Motion variant
   but a requestAnimationFrame helper that matches Joby's feel.
   ===================================================================== */

export function animateCountUp(
  from: number,
  to: number,
  durationMs: number,
  onUpdate: (value: number) => void,
  onComplete?: () => void
) {
  const start = performance.now();
  const isDecimal = !Number.isInteger(to);
  let raf: number;

  const tick = (t: number) => {
    const p = Math.min(1, (t - start) / durationMs);
    // ease-out cubic (matches Joby's stat reveal feel)
    const eased = 1 - Math.pow(1 - p, 3);
    const value = from + (to - from) * eased;
    onUpdate(isDecimal ? value : Math.round(value));
    if (p < 1) {
      raf = requestAnimationFrame(tick);
    } else {
      onComplete?.();
    }
  };

  raf = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(raf);
}
