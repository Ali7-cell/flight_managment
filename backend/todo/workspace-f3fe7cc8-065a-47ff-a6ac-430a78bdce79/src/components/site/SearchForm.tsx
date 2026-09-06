"use client";

import { useState, useEffect, useTransition, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plane, Calendar, Users, ArrowRight, Search, X, ChevronDown } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";
import type { Airport, CabinClass } from "@/lib/types";
import { cn } from "@/lib/utils";
import { cabinLabel } from "@/lib/format";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

// Airport autocomplete input
function AirportField({
  label,
  value,
  onChange,
  placeholder,
  align = "left",
}: {
  label: string;
  value: string;
  onChange: (code: string, airport: Airport | null) => void;
  placeholder: string;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Airport[]>([]);
  const [loading, setLoading] = useState(false);
  const [displayCode, setDisplayCode] = useState(value);
  const [displayCity, setDisplayCity] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Resolve current value to display text
  useEffect(() => {
    let cancelled = false;
    if (value) {
      fetch(`/api/airports?q=${encodeURIComponent(value)}&limit=1`)
        .then((r) => r.json())
        .then((data) => {
          if (cancelled) return;
          const a: Airport | undefined = data.airports?.[0];
          if (a) {
            setDisplayCode(a.code);
            setDisplayCity(a.city);
          }
        })
        .catch(() => {});
    }
    return () => {
      cancelled = true;
    };
  }, [value]);

  // Debounced search
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await fetch(`/api/airports?q=${encodeURIComponent(q)}&limit=12`);
        const data = await r.json();
        if (!cancelled) {
          setResults(data.airports || []);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 180);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q, open]);

  // Close on outside click
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  return (
    <div ref={containerRef} className="relative flex-1 min-w-0">
      <label className="absolute left-4 top-2 text-[10px] font-semibold uppercase tracking-widest text-ink/60 z-10">
        {label}
      </label>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "w-full h-[76px] rounded-full bg-cream/40 hover:bg-cream/60 transition-colors pl-5 pr-4 pt-7 pb-2 text-left border border-ink/10 focus:border-sky focus:outline-none",
          align === "right" && "text-right pr-5 pl-4"
        )}
      >
        <span className="flex items-baseline gap-2" style={{ justifyContent: align === "right" ? "flex-end" : "flex-start" }}>
          <span className="text-xl font-semibold font-display tracking-tight">{displayCode || placeholder}</span>
          {displayCity && (
            <span className="text-sm text-ink/60 truncate max-w-[140px]">{displayCity}</span>
          )}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25, ease: JOB_EASE }}
            className={cn(
              "absolute z-50 mt-2 w-full bg-white rounded-2xl shadow-2xl shadow-ink/15 border border-ink/10 overflow-hidden",
              align === "right" ? "left-0" : "left-0"
            )}
          >
            <div className="p-3 border-b border-ink/10">
              <input
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search city, code, or country…"
                className="w-full bg-cream/50 rounded-full px-4 py-2.5 text-sm outline-none border border-transparent focus:border-sky"
              />
            </div>
            <div className="max-h-72 overflow-y-auto scrollbar-thin">
              {loading && (
                <div className="px-4 py-6 text-sm text-ink/50 text-center">Searching…</div>
              )}
              {!loading && results.length === 0 && (
                <div className="px-4 py-6 text-sm text-ink/50 text-center">No airports found.</div>
              )}
              {!loading &&
                results.map((a) => (
                  <button
                    key={a.code}
                    onClick={() => {
                      onChange(a.code, a);
                      setDisplayCode(a.code);
                      setDisplayCity(a.city);
                      setOpen(false);
                      setQ("");
                    }}
                    className="w-full px-4 py-3 hover:bg-cream/60 transition-colors flex items-center gap-3 text-left"
                  >
                    <span className="font-display font-semibold text-base w-12 shrink-0">{a.code}</span>
                    <span className="flex-1 min-w-0">
                      <div className="text-sm text-ink truncate">{a.city}, {a.country}</div>
                      <div className="text-xs text-ink/50 truncate">{a.name}</div>
                    </span>
                  </button>
                ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Passengers dropdown
function PassengersField({
  value,
  onChange,
}: {
  value: number;
  onChange: (n: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const labelFor = (n: number) => (n === 1 ? "1 passenger" : `${n} passengers`);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="h-[76px] w-full md:w-auto md:min-w-[180px] rounded-full bg-cream/40 hover:bg-cream/60 transition-colors pl-5 pr-4 pt-7 pb-2 text-left border border-ink/10 focus:border-sky focus:outline-none"
      >
        <span className="absolute left-4 top-2 text-[10px] font-semibold uppercase tracking-widest text-ink/60">
          Passengers
        </span>
        <span className="text-base font-semibold font-display">{labelFor(value)}</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25, ease: JOB_EASE }}
            className="absolute z-50 mt-2 w-full md:w-64 bg-white rounded-2xl shadow-2xl shadow-ink/15 border border-ink/10 p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Adults</span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onChange(Math.max(1, value - 1))}
                  className="w-8 h-8 rounded-full bg-cream/60 hover:bg-cream text-ink font-semibold disabled:opacity-30"
                  disabled={value <= 1}
                >
                  −
                </button>
                <span className="w-8 text-center font-semibold">{value}</span>
                <button
                  onClick={() => onChange(Math.min(9, value + 1))}
                  className="w-8 h-8 rounded-full bg-cream/60 hover:bg-cream text-ink font-semibold disabled:opacity-30"
                  disabled={value >= 9}
                >
                  +
                </button>
              </div>
            </div>
            <p className="text-xs text-ink/50">Maximum 9 passengers per booking.</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Cabin class field
function CabinField({
  value,
  onChange,
}: {
  value: CabinClass;
  onChange: (c: CabinClass) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="h-[76px] w-full md:w-auto md:min-w-[180px] rounded-full bg-cream/40 hover:bg-cream/60 transition-colors pl-5 pr-4 pt-7 pb-2 text-left border border-ink/10 focus:border-sky focus:outline-none flex items-center justify-between"
      >
        <span>
          <span className="absolute left-4 top-2 text-[10px] font-semibold uppercase tracking-widest text-ink/60">
            Cabin
          </span>
          <span className="text-base font-semibold font-display">{cabinLabel(value)}</span>
        </span>
        <ChevronDown className="w-4 h-4 text-ink/60 mt-3" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25, ease: JOB_EASE }}
            className="absolute z-50 mt-2 w-full md:w-48 bg-white rounded-2xl shadow-2xl shadow-ink/15 border border-ink/10 overflow-hidden"
          >
            {(["economy", "business", "first"] as CabinClass[]).map((c) => (
              <button
                key={c}
                onClick={() => {
                  onChange(c);
                  setOpen(false);
                }}
                className={cn(
                  "w-full px-4 py-3 text-left text-sm hover:bg-cream/60 transition-colors",
                  value === c && "bg-sky/10 text-sky font-medium"
                )}
              >
                {cabinLabel(c)}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function SearchForm() {
  const { query, setQuery, setFlights, setResultsLoading, setStep } = useBookingStore();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const onSearch = async () => {
    if (!query.from || !query.to) {
      setError("Please select both origin and destination airports.");
      return;
    }
    if (query.from === query.to) {
      setError("Origin and destination cannot be the same.");
      return;
    }
    setError(null);
    setResultsLoading(true);
    setStep("results");
    startTransition(async () => {
      try {
        const url = `/api/flights?from=${encodeURIComponent(query.from)}&to=${encodeURIComponent(query.to)}&date=${encodeURIComponent(query.date)}&limit=50`;
        const r = await fetch(url);
        const data = await r.json();
        setFlights(data.flights || []);
      } catch (e) {
        setFlights([]);
      } finally {
        setResultsLoading(false);
      }
    });
    // Smooth-scroll to results
    setTimeout(() => {
      document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  };

  return (
    <div className="w-full">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: JOB_EASE, delay: 0.3 }}
        className="bg-white/95 backdrop-blur-md rounded-full p-2 shadow-2xl shadow-ink/20 border border-ink/10"
      >
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-2">
          <AirportField
            label="From"
            value={query.from}
            placeholder="JFK"
            onChange={(code) => setQuery({ from: code })}
          />
          <div className="hidden md:flex items-center justify-center px-1">
            <div className="w-10 h-10 rounded-full bg-ink text-cream flex items-center justify-center shrink-0">
              <Plane className="w-4 h-4 -rotate-45" />
            </div>
          </div>
          <AirportField
            label="To"
            value={query.to}
            placeholder="LHR"
            align="right"
            onChange={(code) => setQuery({ to: code })}
          />
          <div className="flex-1 min-w-0">
            <label className="absolute left-4 top-2 text-[10px] font-semibold uppercase tracking-widest text-ink/60 z-10 pointer-events-none">
              Date
            </label>
            <input
              type="date"
              value={query.date}
              min={new Date().toISOString().split("T")[0]}
              onChange={(e) => setQuery({ date: e.target.value })}
              className="w-full h-[76px] rounded-full bg-cream/40 hover:bg-cream/60 transition-colors pl-5 pr-4 pt-7 pb-2 text-base font-semibold font-display border border-ink/10 focus:border-sky focus:outline-none"
            />
          </div>
          <PassengersField
            value={query.passengers}
            onChange={(n) => setQuery({ passengers: n })}
          />
          <CabinField
            value={query.cabin}
            onChange={(c) => setQuery({ cabin: c })}
          />
          <button
            onClick={onSearch}
            disabled={isPending}
            className="h-[76px] md:px-8 px-6 rounded-full bg-ink text-cream font-semibold text-base hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] flex items-center justify-center gap-2 shrink-0 disabled:opacity-50 group"
          >
            <Search className="w-4 h-4 group-hover:rotate-12 transition-transform duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]" />
            <span>Search</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]" />
          </button>
        </div>
      </motion.div>
      {error && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-3 text-sm text-sunset px-4"
        >
          {error}
        </motion.p>
      )}
    </div>
  );
}
