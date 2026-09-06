"use client";

import { motion } from "framer-motion";
import { Search, MousePointerClick, Plane } from "lucide-react";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const STEPS = [
  {
    n: "01",
    icon: Search,
    title: "Search",
    body: "Type in any city or airport code. Skyway instantly surfaces live flights across our 21-airport network.",
  },
  {
    n: "02",
    icon: MousePointerClick,
    title: "Select",
    body: "Compare fares across Economy, Business, and First. Pick the seat you want, the way you want, on a live seat map.",
  },
  {
    n: "03",
    icon: Plane,
    title: "Fly",
    body: "Lock in your booking in under 60 seconds. Receive your boarding reference by email — that&apos;s it, you&apos;re cleared for takeoff.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="py-24 md:py-32 bg-ink text-cream overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: JOB_EASE }}
        >
          <div className="text-xs font-semibold uppercase tracking-widest text-sky mb-4">
            How it works
          </div>
          <h2 className="font-display font-semibold tracking-tight text-[clamp(2.25rem,5vw,4rem)] leading-[0.95] max-w-3xl">
            Three taps to takeoff.
          </h2>
        </motion.div>

        <div className="mt-12 md:mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-10">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.n}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.7, ease: JOB_EASE, delay: i * 0.15 }}
                className="relative"
              >
                {/* Connector line on desktop */}
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-12 left-[calc(50%+40px)] right-[-10%] h-[1px] bg-cream/15" />
                )}
                <div className="relative">
                  <div className="w-24 h-24 rounded-full border border-cream/20 flex items-center justify-center mb-6 relative">
                    <Icon className="w-9 h-9 text-sky" />
                    <span className="absolute -top-2 -right-2 bg-sky text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                      {s.n}
                    </span>
                  </div>
                  <h3 className="font-display text-3xl md:text-4xl font-semibold tracking-tight mb-3">{s.title}</h3>
                  <p
                    className="text-cream/70 text-base md:text-lg max-w-sm leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: s.body }}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
