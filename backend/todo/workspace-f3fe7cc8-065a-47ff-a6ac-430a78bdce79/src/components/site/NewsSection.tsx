"use client";

import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const NEWS = [
  {
    category: "Routes",
    date: "Sep 2026",
    title: "Skyway launches daily nonstop between JFK and Karachi",
    excerpt: "Our newest route connects two iconic cities with a brand new A350-900, offering flat-bed First and full business Wi-Fi.",
    gradient: "from-[#007AE5] to-[#1C3F99]",
  },
  {
    category: "Fleet",
    date: "Aug 2026",
    title: "Inside the all-new Skyway First Class suite",
    excerpt: "Privacy doors, 32-inch displays, and a personal wardrobe. A first look at our upcoming flagship cabin refresh.",
    gradient: "from-[#083E6F] to-[#0E1620]",
  },
  {
    category: "Experience",
    date: "Aug 2026",
    title: "How we cut average boarding time to 12 minutes",
    excerpt: "A small change to seat assignment logic reduced boarding time by 38% across our network. Here's the story.",
    gradient: "from-[#EB6110] to-[#7C2D08]",
  },
];

export function NewsSection() {
  return (
    <section id="news" className="py-24 md:py-32 bg-cream text-ink overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: JOB_EASE }}
          className="flex flex-col md:flex-row md:items-end md:justify-between gap-6"
        >
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-sky mb-4">
              News from above
            </div>
            <h2 className="font-display font-semibold tracking-tight text-[clamp(2.25rem,5vw,4rem)] leading-[0.95] max-w-2xl">
              The sky was never the limit.
            </h2>
          </div>
          <button className="hidden md:inline-flex items-center gap-2 nav-underline text-sm font-medium text-ink/70 hover:text-ink">
            All stories <ArrowUpRight className="w-4 h-4" />
          </button>
        </motion.div>

        <div className="mt-12 md:mt-16 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
          {NEWS.map((n, i) => (
            <motion.button
              key={n.title}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.6, ease: JOB_EASE, delay: i * 0.1 }}
              whileHover={{ y: -6 }}
              className="group text-left rounded-3xl overflow-hidden bg-white border border-ink/10 shadow-sm hover:shadow-xl shadow-ink/10 transition-shadow duration-500"
            >
              {/* Image block (gradient + plane emoji-removed) */}
              <div className={`relative h-56 bg-gradient-to-br ${n.gradient} overflow-hidden`}>
                <motion.div
                  className="absolute inset-0"
                  animate={{ scale: [1, 1.06, 1] }}
                  transition={{ duration: 12 + i * 2, repeat: Infinity, ease: "easeInOut" }}
                  style={{
                    backgroundImage: `radial-gradient(circle at 30% 70%, rgba(255,217,201,0.25) 0%, transparent 50%), radial-gradient(circle at 70% 30%, rgba(245,244,223,0.18) 0%, transparent 50%)`,
                  }}
                />
                <div className="absolute bottom-4 left-4 px-3 py-1.5 rounded-full bg-cream/20 backdrop-blur-sm text-cream text-xs font-semibold uppercase tracking-widest">
                  {n.category}
                </div>
                <ArrowUpRight className="absolute top-4 right-4 w-5 h-5 text-cream/70 group-hover:text-cream group-hover:rotate-12 transition-all duration-500" />
              </div>

              <div className="p-6">
                <div className="text-xs text-ink/50 uppercase tracking-wider mb-2">{n.date}</div>
                <h3 className="font-display text-xl font-semibold tracking-tight leading-snug mb-3 group-hover:text-sky transition-colors duration-300">
                  {n.title}
                </h3>
                <p className="text-sm text-ink/70 leading-relaxed">{n.excerpt}</p>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </section>
  );
}
