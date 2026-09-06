"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const STATS = [
  { value: 540, suffix: "", label: "Daily flights across our network" },
  { value: 21, suffix: "", label: "Destinations on six continents" },
  { value: 99, suffix: "%", label: "On-time arrival, every single day" },
  { value: 4.9, suffix: "★", label: "Average passenger rating" },
];

function CountUp({ value, suffix, duration = 1.6 }: { value: number; suffix: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const [display, setDisplay] = useState(0);
  const isDecimal = !Number.isInteger(value);

  useEffect(() => {
    if (!inView) return;
    let raf: number;
    const start = performance.now();
    const animate = (t: number) => {
      const p = Math.min(1, (t - start) / (duration * 1000));
      // ease-out cubic
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(value * eased);
      if (p < 1) raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [inView, value, duration]);

  const formatted = isDecimal
    ? display.toFixed(1)
    : Math.round(display).toLocaleString();

  return (
    <span ref={ref} className="font-display font-semibold tracking-tight">
      {formatted}
      <span className="text-sky">{suffix}</span>
    </span>
  );
}

export function Stats() {
  return (
    <section id="fleet" className="py-24 md:py-32 bg-cream text-ink overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: JOB_EASE }}
        >
          <div className="text-xs font-semibold uppercase tracking-widest text-sky mb-4">
            By the numbers
          </div>
          <h2 className="font-display font-semibold tracking-tight text-[clamp(2.25rem,5vw,4rem)] leading-[0.95] max-w-3xl">
            Numbers we&apos;re proud of.
          </h2>
        </motion.div>

        <div className="mt-14 md:mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-10">
          {STATS.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 0.6, ease: JOB_EASE, delay: i * 0.1 }}
              className="border-t border-ink/15 pt-6"
            >
              <div className="font-display text-[clamp(2.5rem,5vw,4rem)] leading-none mb-3">
                <CountUp value={s.value} suffix={s.suffix} />
              </div>
              <p className="text-sm text-ink/60 leading-snug">{s.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
