"use client";

import { motion } from "framer-motion";
import { ArrowRight, Plane } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

// Featured popular routes — uses the cream + sky-blue palette, no external images.
const ROUTES = [
  { from: "JFK", fromCity: "New York", to: "LHR", toCity: "London",     price: 412, duration: "7h 05m", gradient: "from-[#007AE5] to-[#1C3F99]" },
  { from: "LAX", fromCity: "Los Angeles", to: "SYD", toCity: "Sydney",  price: 938, duration: "13h 35m", gradient: "from-[#EB6110] to-[#7C2D08]" },
  { from: "DXB", fromCity: "Dubai", to: "KHI", toCity: "Karachi",       price: 198, duration: "2h 05m", gradient: "from-[#FFD9C9] to-[#EB6110]" },
  { from: "SFO", fromCity: "San Francisco", to: "NRT", toCity: "Tokyo", price: 687, duration: "11h 25m", gradient: "from-[#083E6F] to-[#0E1620]" },
  { from: "SIN", fromCity: "Singapore", to: "HKG", toCity: "Hong Kong", price: 167, duration: "3h 50m", gradient: "from-[#1C3F99] to-[#007AE5]" },
  { from: "CDG", fromCity: "Paris", to: "JFK", toCity: "New York",       price: 389, duration: "8h 15m", gradient: "from-[#007AE5] to-[#083E6F]" },
];

export function FeaturedRoutes() {
  const { setQuery, setStep, setResultsLoading, setFlights } = useBookingStore();

  const quickSearch = async (from: string, to: string) => {
    setQuery({ from, to });
    setStep("results");
    setResultsLoading(true);
    try {
      const r = await fetch(`/api/flights?from=${from}&to=${to}&limit=50`);
      const data = await r.json();
      setFlights(data.flights || []);
    } catch {
      setFlights([]);
    } finally {
      setResultsLoading(false);
    }
    setTimeout(() => {
      document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  };

  return (
    <section id="routes" className="relative py-24 md:py-32 bg-cream text-ink overflow-hidden">
      {/* Section eyebrow */}
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: JOB_EASE }}
        >
          <div className="text-xs font-semibold uppercase tracking-widest text-sky mb-4">
            Popular routes
          </div>
          <h2 className="font-display font-semibold tracking-tight text-[clamp(2.25rem,5vw,4rem)] leading-[0.95] max-w-3xl">
            With routes like these, there&apos;s
            <span className="block">nowhere to go but up.</span>
          </h2>
          <p className="mt-5 max-w-xl text-ink/70 text-lg">
            Six handpicked routes to start your next journey. Tap any card to see live availability and pricing.
          </p>
        </motion.div>

        {/* Cards grid */}
        <div className="mt-12 md:mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {ROUTES.map((route, idx) => (
            <motion.button
              key={route.from + route.to}
              onClick={() => quickSearch(route.from, route.to)}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.6, ease: JOB_EASE, delay: idx * 0.08 }}
              whileHover={{ y: -6 }}
              className={`group relative overflow-hidden rounded-3xl bg-gradient-to-br ${route.gradient} aspect-[4/3] text-left text-cream p-6 shadow-lg shadow-ink/10`}
            >
              {/* Plane illustration */}
              <motion.div
                className="absolute -bottom-6 -right-6 opacity-20"
                animate={{ y: [0, -8, 0], rotate: [-2, 4, -2] }}
                transition={{ duration: 4 + idx, repeat: Infinity, ease: "easeInOut" }}
              >
                <Plane className="w-44 h-44 -rotate-45 fill-cream/20" />
              </motion.div>

              {/* Hover arrow */}
              <div className="absolute top-6 right-6 w-10 h-10 rounded-full bg-cream/20 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]">
                <ArrowRight className="w-4 h-4" />
              </div>

              {/* Route info */}
              <div className="relative z-10 flex flex-col h-full justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-display text-3xl font-semibold tracking-tight">{route.from}</span>
                    <Plane className="w-4 h-4 -rotate-0" />
                    <span className="font-display text-3xl font-semibold tracking-tight">{route.to}</span>
                  </div>
                  <div className="text-sm text-cream/80">{route.fromCity} → {route.toCity}</div>
                </div>
                <div className="flex items-end justify-between mt-6">
                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-cream/60">From</div>
                    <div className="font-display text-2xl font-semibold">${route.price}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] uppercase tracking-widest text-cream/60">Duration</div>
                    <div className="font-display text-base font-medium">{route.duration}</div>
                  </div>
                </div>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </section>
  );
}
