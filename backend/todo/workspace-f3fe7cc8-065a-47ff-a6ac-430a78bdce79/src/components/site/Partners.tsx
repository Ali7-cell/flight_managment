"use client";

import { motion } from "framer-motion";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const PARTNERS = [
  "Skyway Air",
  "Meridian",
  "Atlas Alliance",
  "NorthStar",
  "Pacific Link",
  "Cirrus",
  "Voyager",
  "Helios",
  "Solstice",
  "Aurora",
];

export function Partners() {
  // Duplicate the list to create seamless marquee
  const marquee = [...PARTNERS, ...PARTNERS];

  return (
    <section className="py-20 md:py-24 bg-cream border-y border-ink/10 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 mb-10">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: JOB_EASE }}
          className="text-center"
        >
          <div className="text-xs font-semibold uppercase tracking-widest text-ink/60 mb-3">
            Trusted by travellers worldwide
          </div>
          <h2 className="font-display font-semibold tracking-tight text-3xl md:text-4xl">
            Operating with the best.
          </h2>
        </motion.div>
      </div>

      {/* Marquee */}
      <div className="relative">
        {/* edge fade */}
        <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-cream to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-cream to-transparent z-10 pointer-events-none" />

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="flex animate-marquee"
        >
          {marquee.map((p, i) => (
            <div
              key={p + i}
              className="flex items-center gap-3 px-10 py-4 shrink-0 group"
            >
              <div className="w-8 h-8 rounded-full bg-ink/8 group-hover:bg-sky/20 transition-colors duration-500" />
              <span className="font-display text-2xl md:text-3xl font-semibold tracking-tight text-ink/40 group-hover:text-ink/80 transition-colors duration-500">
                {p}
              </span>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
