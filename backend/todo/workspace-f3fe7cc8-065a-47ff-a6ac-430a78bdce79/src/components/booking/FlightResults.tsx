"use client";

import { motion } from "framer-motion";
import { ArrowLeft, Plane, AlertCircle, X } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";
import { FlightCard } from "./FlightCard";
import { formatDateLong } from "@/lib/format";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

export function FlightResults() {
  const { flights, resultsLoading, query, reset, setStep } = useBookingStore();

  if (resultsLoading) {
    return (
      <section id="results" className="py-20 bg-cream text-ink min-h-screen">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center py-32">
            <motion.div
              animate={{ y: [0, -10, 0], rotate: [-3, 4, -3] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            >
              <Plane className="w-12 h-12 text-sky -rotate-45" />
            </motion.div>
            <p className="mt-6 text-ink/60 text-lg">Searching live flights…</p>
            <p className="mt-1 text-sm text-ink/40">
              {query.from} → {query.to} · {formatDateLong(query.date + "T00:00:00")}
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="results" className="py-20 md:py-24 bg-cream text-ink min-h-screen">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: JOB_EASE }}
          className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8 md:mb-12"
        >
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-sky mb-3">
              {flights.length > 0 ? `${flights.length} flights found` : "Search results"}
            </div>
            <h2 className="font-display font-semibold tracking-tight text-[clamp(2rem,4vw,3rem)] leading-[0.95]">
              {query.from} <span className="text-ink/40">→</span> {query.to}
            </h2>
            <p className="mt-2 text-ink/60">
              {formatDateLong(query.date + "T00:00:00")} · {query.passengers}{" "}
              {query.passengers === 1 ? "passenger" : "passengers"} ·{" "}
              {query.cabin.charAt(0).toUpperCase() + query.cabin.slice(1)}
            </p>
          </div>
          <button
            onClick={() => {
              reset();
              setStep("search");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            className="inline-flex items-center gap-2 text-sm font-medium text-ink/70 hover:text-ink transition-colors nav-underline"
          >
            <ArrowLeft className="w-4 h-4" /> New search
          </button>
        </motion.div>

        {/* Results list */}
        {flights.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: JOB_EASE, delay: 0.2 }}
            className="bg-white rounded-3xl border border-ink/10 p-12 text-center"
          >
            <AlertCircle className="w-10 h-10 text-sunset mx-auto mb-4" />
            <h3 className="font-display text-2xl font-semibold tracking-tight mb-2">
              No flights on this route for the selected date.
            </h3>
            <p className="text-ink/60 max-w-md mx-auto mb-6">
              Try a different date or choose another route. We&apos;re constantly adding new connections.
            </p>
            <button
              onClick={() => {
                reset();
                setStep("search");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              className="px-6 h-12 rounded-full bg-ink text-cream font-medium hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] inline-flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" /> Back to search
            </button>
          </motion.div>
        ) : (
          <div className="space-y-3">
            {flights.map((f, i) => (
              <FlightCard key={f.id} flight={f} index={i} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
