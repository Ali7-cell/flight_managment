"use client";

import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, Plane } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";
import { seatsToGrid, cabinLabel, formatMoney, formatDuration, formatTime, formatDate } from "@/lib/format";
import type { CabinClass } from "@/lib/types";
import { cn } from "@/lib/utils";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const CABIN_COLORS: Record<CabinClass, { bg: string; border: string; text: string }> = {
  first:    { bg: "bg-sunset/15",  border: "border-sunset",  text: "text-sunset"  },
  business: { bg: "bg-sky/15",     border: "border-sky",     text: "text-sky"     },
  economy:  { bg: "bg-ink/10",     border: "border-ink/40", text: "text-ink/70"  },
};

export function SeatSelection() {
  const { seats, selectedFlight, selectedSeat, selectSeat, setStep, query } = useBookingStore();
  const [userCabin, setUserCabin] = useState<CabinClass>(query.cabin);

  const grid = useMemo(() => seatsToGrid(seats), [seats]);

  // Derive the cabin we should actually display — falls back if the user's pick is empty.
  const activeCabin = useMemo<CabinClass>(() => {
    const hasCabin = seats.some((s) => s.isAvailable && s.cabinClass === userCabin);
    if (hasCabin) return userCabin;
    const fallback = seats.find((s) => s.isAvailable)?.cabinClass;
    return fallback || userCabin;
  }, [seats, userCabin]);

  const availableByCabin = useMemo(() => {
    const counts = { economy: 0, business: 0, first: 0 } as Record<CabinClass, number>;
    for (const s of seats) {
      if (s.isAvailable && s.cabinClass === activeCabin) counts[activeCabin]++;
    }
    return counts;
  }, [seats, activeCabin]);

  if (!selectedFlight) return null;

  const onContinue = () => {
    if (selectedSeat) setStep("passenger");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
            Choose your seat
          </h3>
          <p className="text-ink/60 text-sm mt-1">
            {selectedFlight.fromAirport.code} → {selectedFlight.toAirport.code} ·{" "}
            {formatDate(selectedFlight.departureTime)} · {formatTime(selectedFlight.departureTime)}
          </p>
        </div>
        {/* Cabin switch */}
        <div className="inline-flex items-center bg-cream/60 rounded-full p-1">
          {(["economy", "business", "first"] as CabinClass[]).map((c) => {
            const count = seats.filter((s) => s.isAvailable && s.cabinClass === c).length;
            return (
              <button
                key={c}
                onClick={() => setUserCabin(c)}
                disabled={count === 0}
                className={cn(
                  "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-300 ease-[cubic-bezier(0.65,0,0.35,1)] disabled:opacity-30 disabled:cursor-not-allowed",
                  activeCabin === c ? "bg-ink text-cream" : "text-ink/70 hover:text-ink"
                )}
              >
                {cabinLabel(c)}
                <span className="ml-1.5 text-xs opacity-60">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
        {/* Seat map */}
        <div className="bg-white rounded-3xl border border-ink/10 p-6 md:p-8">
          {/* Plane nose */}
          <div className="flex flex-col items-center mb-6">
            <div className="w-32 h-12 rounded-t-full bg-ink/8 flex items-center justify-center">
              <Plane className="w-5 h-5 text-ink/40 rotate-90" />
            </div>
          </div>

          {/* Seat grid */}
          <div className="max-h-[420px] overflow-y-auto scrollbar-thin pr-2">
            <div className="flex flex-col gap-2 items-center">
              {grid.map((row) => {
                const rowCabin = row.cells.find((c) => c)?.cabinClass || "economy";
                const isActiveCabin = rowCabin === activeCabin;
                return (
                  <div
                    key={row.row}
                    className={cn(
                      "flex items-center gap-2 transition-opacity duration-300 ease-[cubic-bezier(0.65,0,0.35,1)]",
                      isActiveCabin ? "opacity-100" : "opacity-30 grayscale"
                    )}
                  >
                    <div className="w-6 text-right text-xs text-ink/40 font-medium">{row.row}</div>
                    {/* A B C */}
                    <div className="flex gap-2">
                      {row.cells.slice(0, 3).map((seat) => (
                        <SeatButton
                          key={seat?.seatNumber || row.row + (seat?.column || "")}
                          seat={seat}
                          selected={selectedSeat?.seatNumber === seat?.seatNumber}
                          onSelect={() => seat && selectSeat(seat.isAvailable ? seat : null)}
                        />
                      ))}
                    </div>
                    {/* Aisle */}
                    <div className="w-8 text-center text-xs text-ink/30">·</div>
                    {/* D E F */}
                    <div className="flex gap-2">
                      {row.cells.slice(3, 6).map((seat) => (
                        <SeatButton
                          key={seat?.seatNumber || row.row + (seat?.column || "")}
                          seat={seat}
                          selected={selectedSeat?.seatNumber === seat?.seatNumber}
                          onSelect={() => seat && selectSeat(seat.isAvailable ? seat : null)}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Legend */}
          <div className="mt-6 flex items-center justify-center gap-5 flex-wrap text-xs">
            <Legend color="bg-white border border-ink/30" label="Available" />
            <Legend color="bg-sky" label="Selected" dark />
            <Legend color="bg-ink/15" label="Taken" />
          </div>
        </div>

        {/* Selection summary */}
        <div className="bg-white rounded-3xl border border-ink/10 p-6 h-fit sticky top-24">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-ink/50 mb-4">
            Your selection
          </h4>
          <AnimatePresence mode="wait">
            {selectedSeat ? (
              <motion.div
                key="selected"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3, ease: JOB_EASE }}
                className="space-y-4"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      "w-12 h-12 rounded-2xl flex items-center justify-center font-display text-lg font-semibold",
                      CABIN_COLORS[selectedSeat.cabinClass].bg,
                      "border-2",
                      CABIN_COLORS[selectedSeat.cabinClass].border,
                      CABIN_COLORS[selectedSeat.cabinClass].text
                    )}
                  >
                    {selectedSeat.seatNumber}
                  </div>
                  <div>
                    <div className="font-semibold">{cabinLabel(selectedSeat.cabinClass)} class</div>
                    <div className="text-sm text-ink/60">Row {selectedSeat.row}, seat {selectedSeat.column}</div>
                  </div>
                </div>
                <div className="border-t border-ink/10 pt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-ink/60">Base fare</span>
                    <span>{formatMoney(selectedSeat.price)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink/60">Taxes & fees</span>
                    <span>$0</span>
                  </div>
                  <div className="flex justify-between font-semibold pt-2 border-t border-ink/10">
                    <span>Total</span>
                    <span className="font-display text-lg">{formatMoney(selectedSeat.price)}</span>
                  </div>
                </div>
                <button
                  onClick={onContinue}
                  className="w-full h-12 rounded-full bg-ink text-cream font-medium hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] flex items-center justify-center gap-2 group"
                >
                  Continue
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-500" />
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="text-center py-8"
              >
                <div className="w-12 h-12 rounded-full bg-cream/60 mx-auto mb-3 flex items-center justify-center">
                  <Plane className="w-5 h-5 text-ink/40 -rotate-45" />
                </div>
                <p className="text-sm text-ink/60">
                  Pick a seat on the map to see pricing and continue.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function SeatButton({
  seat,
  selected,
  onSelect,
}: {
  seat: any | null;
  selected: boolean;
  onSelect: () => void;
}) {
  if (!seat) return <div className="w-9 h-9" />;
  const styles = seat.isAvailable
    ? selected
      ? "bg-sky text-cream border-sky scale-105 shadow-lg shadow-sky/30"
      : "bg-white text-ink/70 border-ink/20 hover:border-sky hover:bg-sky/5"
    : "bg-ink/15 text-ink/30 border-ink/15 cursor-not-allowed";

  return (
    <motion.button
      whileHover={seat.isAvailable ? { scale: selected ? 1 : 1.05 } : {}}
      whileTap={seat.isAvailable ? { scale: 0.95 } : {}}
      transition={{ duration: 0.2, ease: JOB_EASE }}
      onClick={onSelect}
      disabled={!seat.isAvailable}
      className={cn(
        "w-9 h-9 rounded-xl border text-xs font-medium transition-all duration-300 ease-[cubic-bezier(0.65,0,0.35,1)] flex items-center justify-center",
        styles
      )}
      title={`Seat ${seat.seatNumber} · ${cabinLabel(seat.cabinClass)} · ${seat.isAvailable ? formatMoney(seat.price) : "Taken"}`}
    >
      {seat.column}
      {selected && <Check className="w-3 h-3 absolute" />}
    </motion.button>
  );
}

function Legend({ color, label, dark = false }: { color: string; label: string; dark?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={cn("w-4 h-4 rounded-md", color)} />
      <span className={dark ? "text-ink/70" : "text-ink/60"}>{label}</span>
    </div>
  );
}
