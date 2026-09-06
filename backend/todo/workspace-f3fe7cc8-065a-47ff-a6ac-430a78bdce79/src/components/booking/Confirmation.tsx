"use client";

import { motion } from "framer-motion";
import { Check, Plane, Calendar, Clock, MapPin, User, Mail, Download, Home } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";
import { formatTime, formatDateLong, formatDuration, formatMoney, cabinLabel } from "@/lib/format";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

export function Confirmation() {
  const { booking, selectedFlight, selectedSeat, passenger, reset, setStep } = useBookingStore();

  const flight = booking?.flight || selectedFlight;
  if (!flight || !booking) return null;

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Hero check */}
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: JOB_EASE }}
        className="text-center"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.6, ease: JOB_EASE, delay: 0.1 }}
          className="w-20 h-20 rounded-full bg-sky text-white flex items-center justify-center mx-auto mb-4"
        >
          <Check className="w-10 h-10" strokeWidth={3} />
        </motion.div>
        <h2 className="font-display text-3xl md:text-5xl font-semibold tracking-tight">
          You&apos;re cleared for takeoff.
        </h2>
        <p className="text-ink/60 mt-2">
          A confirmation has been sent to <span className="font-medium text-ink">{booking.passengerEmail}</span>.
        </p>
      </motion.div>

      {/* Boarding pass */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: JOB_EASE, delay: 0.2 }}
        className="relative bg-white rounded-3xl border border-ink/10 overflow-hidden shadow-xl shadow-ink/10"
      >
        {/* Perforation */}
        <div className="absolute left-0 right-0 top-[55%] border-t border-dashed border-ink/15" />
        <div className="absolute left-[-12px] top-[55%] w-6 h-6 rounded-full bg-cream -translate-y-1/2" />
        <div className="absolute right-[-12px] top-[55%] w-6 h-6 rounded-full bg-cream -translate-y-1/2" />

        {/* Top section: airline + reference */}
        <div className="bg-ink text-cream p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-cream text-ink flex items-center justify-center">
              <Plane className="w-5 h-5 -rotate-45" />
            </div>
            <div>
              <div className="font-display text-xl font-semibold tracking-tight">Skyway Air</div>
              <div className="text-xs text-cream/60">Boarding pass</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-widest text-cream/60">Reference</div>
            <div className="font-mono font-semibold text-lg tracking-wider">{booking.reference}</div>
          </div>
        </div>

        {/* Main section */}
        <div className="p-6 md:p-8 grid grid-cols-2 md:grid-cols-4 gap-6">
          <Detail icon={MapPin} label="From" value={flight.fromAirport.code} sub={flight.fromAirport.city} />
          <Detail icon={MapPin} label="To" value={flight.toAirport.code} sub={flight.toAirport.city} />
          <Detail icon={Calendar} label="Date" value={formatDateLong(flight.departureTime).split(",")[0]} sub={formatDateLong(flight.departureTime).split(",").slice(1).join(",")} />
          <Detail icon={Clock} label="Departs" value={formatTime(flight.departureTime)} sub={`Duration ${formatDuration(flight.durationMin)}`} />
          <Detail icon={User} label="Passenger" value={passenger.name} sub={booking.passengerEmail} />
          <Detail icon={Plane} label="Flight" value={flight.flightNumber} sub={flight.aircraft} />
          <Detail icon={Check} label="Seat" value={booking.seatNumber} sub={cabinLabel(booking.cabinClass as any)} />
          <Detail icon={Check} label="Status" value="Confirmed" sub={flight.gate ? `Gate ${flight.gate}` : "Gate TBA"} />
        </div>

        {/* Bottom strip: barcode */}
        <div className="bg-cream/30 px-6 md:px-8 py-5 flex items-center justify-between border-t border-ink/10">
          <div className="flex items-center gap-1">
            {Array.from({ length: 32 }).map((_, i) => (
              <div
                key={i}
                className="bg-ink"
                style={{
                  width: ((i * 7) % 5 === 0 ? 3 : 1) + "px",
                  height: 36,
                  opacity: (i % 3 === 0 ? 1 : 0.7),
                }}
              />
            ))}
          </div>
          <div className="font-mono text-xs text-ink/60 hidden md:block">
            {booking.reference} · {booking.passengerName.toUpperCase()}
          </div>
        </div>
      </motion.div>

      {/* Total paid */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: JOB_EASE, delay: 0.4 }}
        className="text-center text-sm text-ink/60"
      >
        Total paid: <span className="font-semibold text-ink">{formatMoney(booking.totalAmount)}</span> ·{" "}
        Payment method: <span className="capitalize">{booking.paymentMethod || "card"}</span>
      </motion.div>

      {/* Actions */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="flex flex-col sm:flex-row items-center justify-center gap-3"
      >
        <button
          onClick={() => window.print()}
          className="px-6 h-12 rounded-full border border-ink/15 hover:border-ink/40 text-ink font-medium hover:bg-cream/40 transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] inline-flex items-center gap-2"
        >
          <Download className="w-4 h-4" /> Download boarding pass
        </button>
        <button
          onClick={() => {
            reset();
            setStep("search");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          className="px-6 h-12 rounded-full bg-ink text-cream font-medium hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] inline-flex items-center gap-2"
        >
          <Home className="w-4 h-4" /> Book another flight
        </button>
      </motion.div>
    </div>
  );
}

function Detail({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: any;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-ink/50 mb-1">
        <Icon className="w-3 h-3" />
        {label}
      </div>
      <div className="font-display text-lg md:text-xl font-semibold tracking-tight">{value}</div>
      {sub && <div className="text-xs text-ink/50 mt-0.5 truncate">{sub}</div>}
    </div>
  );
}
