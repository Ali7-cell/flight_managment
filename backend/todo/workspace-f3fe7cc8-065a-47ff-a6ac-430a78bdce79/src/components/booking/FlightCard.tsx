"use client";

import { motion } from "framer-motion";
import { Plane, Clock, ArrowRight } from "lucide-react";
import type { Flight } from "@/lib/types";
import { formatTime, formatDate, formatDuration, priceForCabin, cabinLabel } from "@/lib/format";
import { useBookingStore } from "@/store/booking-store";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

export function FlightCard({ flight, index = 0 }: { flight: Flight; index?: number }) {
  const { query, selectFlight, setStep, setSeats, selectSeat } = useBookingStore();

  const price = priceForCabin(flight, query.cabin);
  const depTime = formatTime(flight.departureTime);
  const arrTime = formatTime(flight.arrivalTime);
  const depDate = formatDate(flight.departureTime);
  const dur = formatDuration(flight.durationMin);
  const cabin = cabinLabel(query.cabin);

  const onSelect = async () => {
    selectFlight(flight);
    selectSeat(null);
    setStep("seats");
    // Pre-fetch seats
    try {
      const r = await fetch(`/api/flights/${flight.id}/seats`);
      const data = await r.json();
      setSeats(data.seats || []);
    } catch {
      setSeats([]);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: JOB_EASE, delay: index * 0.05 }}
      className="group bg-white rounded-2xl border border-ink/10 hover:border-sky/40 transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] overflow-hidden hover:shadow-xl hover:shadow-ink/8"
    >
      <div className="flex flex-col md:flex-row items-stretch">
        {/* Time + route block */}
        <div className="flex-1 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-full bg-ink text-cream flex items-center justify-center shrink-0">
              <Plane className="w-4 h-4 -rotate-45" />
            </div>
            <div>
              <div className="text-sm font-semibold">{flight.airline}</div>
              <div className="text-xs text-ink/50">{flight.flightNumber} · {flight.aircraft}</div>
            </div>
            <div className="ml-auto hidden md:block">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-sky">
                {cabin}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 md:gap-6">
            {/* Departure */}
            <div className="flex-shrink-0">
              <div className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
                {depTime}
              </div>
              <div className="text-sm text-ink/70 font-medium">{flight.fromAirport.code}</div>
              <div className="text-xs text-ink/50">{flight.fromAirport.city}</div>
            </div>

            {/* Duration line */}
            <div className="flex-1 min-w-0 flex flex-col items-center">
              <div className="text-[10px] text-ink/50 mb-1 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {dur}
              </div>
              <div className="relative w-full h-[1px] bg-ink/15">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="bg-white px-2">
                    <Plane className="w-3 h-3 text-ink/40" />
                  </div>
                </div>
              </div>
              <div className="text-[10px] text-ink/40 mt-1">Nonstop</div>
            </div>

            {/* Arrival */}
            <div className="flex-shrink-0 text-right">
              <div className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
                {arrTime}
              </div>
              <div className="text-sm text-ink/70 font-medium">{flight.toAirport.code}</div>
              <div className="text-xs text-ink/50">{flight.toAirport.city}</div>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-4 text-xs text-ink/50">
            <span>{depDate}</span>
            {flight.gate && <span>· Gate {flight.gate}</span>}
            <span>· {flight.availableSeats} seats left</span>
          </div>
        </div>

        {/* Price block */}
        <div className="bg-cream/30 md:bg-transparent border-t md:border-t-0 md:border-l border-ink/10 p-6 flex md:flex-col items-center md:items-end justify-between md:justify-center gap-2 md:min-w-[200px] md:px-7">
          <div className="md:text-right">
            <div className="text-[10px] uppercase tracking-widest text-ink/50">From</div>
            <div className="font-display text-3xl md:text-4xl font-semibold tracking-tight">
              ${Math.round(price)}
            </div>
            <div className="text-xs text-ink/50">{cabin} · per passenger</div>
          </div>
          <button
            onClick={onSelect}
            className="px-6 h-12 rounded-full bg-ink text-cream font-medium hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] flex items-center gap-2 group/btn"
          >
            Select
            <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
