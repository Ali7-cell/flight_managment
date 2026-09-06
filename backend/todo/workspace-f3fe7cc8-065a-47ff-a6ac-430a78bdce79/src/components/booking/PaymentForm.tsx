"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, CreditCard, Wallet, Lock, Check } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";
import { formatMoney, formatTime, formatDate, formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

export function PaymentForm() {
  const { payment, setPayment, selectedFlight, selectedSeat, passenger, setStep, setBooking, setResultsLoading } = useBookingStore();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!selectedFlight || !selectedSeat) return null;

  const total = selectedSeat.price;

  const onPay = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const r = await fetch("/api/booking", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          flightId: selectedFlight.id,
          seatNumber: selectedSeat.seatNumber,
          cabinClass: selectedSeat.cabinClass,
          passengerName: passenger.name,
          passengerEmail: passenger.email,
          passengerPhone: passenger.phone || null,
          paymentMethod: payment.method,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Booking failed");
      setBooking(data.booking);
      setStep("confirmation");
    } catch (e: any) {
      setError(e.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
      {/* Payment form */}
      <div className="space-y-6">
        <div>
          <h3 className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
            Payment
          </h3>
          <p className="text-ink/60 text-sm mt-1 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            Encrypted end-to-end. We never store card details.
          </p>
        </div>

        {/* Method selector */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { id: "card", label: "Card", icon: CreditCard },
            { id: "wallet", label: "Wallet", icon: Wallet },
            { id: "paypal", label: "PayPal", icon: Wallet },
          ].map((m) => {
            const Icon = m.icon;
            const active = payment.method === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setPayment({ method: m.id as any })}
                className={cn(
                  "h-16 rounded-2xl border-2 transition-all duration-300 ease-[cubic-bezier(0.65,0,0.35,1)] flex flex-col items-center justify-center gap-1",
                  active ? "border-sky bg-sky/5 text-sky" : "border-ink/10 text-ink/60 hover:border-ink/30"
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs font-medium">{m.label}</span>
              </button>
            );
          })}
        </div>

        {/* Card fields (only for card method) */}
        {payment.method === "card" && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: JOB_EASE }}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            <PField
              label="Name on card"
              value={payment.cardName}
              onChange={(v) => setPayment({ cardName: v })}
              placeholder="Jane Doe"
              className="md:col-span-2"
            />
            <PField
              label="Card number"
              value={payment.cardNumber}
              onChange={(v) => setPayment({ cardNumber: v.replace(/[^0-9 ]/g, "") })}
              placeholder="1234 5678 9012 3456"
              className="md:col-span-2"
            />
            <PField
              label="Expiry"
              value={payment.expiry}
              onChange={(v) => setPayment({ expiry: v.replace(/[^0-9/]/g, "") })}
              placeholder="MM/YY"
            />
            <PField
              label="CVC"
              value={payment.cvc}
              onChange={(v) => setPayment({ cvc: v.replace(/[^0-9]/g, "").slice(0, 4) })}
              placeholder="123"
            />
          </motion.div>
        )}

        {payment.method !== "card" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="bg-cream/40 border border-ink/10 rounded-2xl p-8 text-center"
          >
            <Wallet className="w-10 h-10 text-ink/40 mx-auto mb-3" />
            <p className="text-sm text-ink/60">
              You&apos;ll be redirected to {payment.method === "wallet" ? "your wallet" : "PayPal"} to complete payment after confirmation.
            </p>
          </motion.div>
        )}

        {error && (
          <div className="bg-sunset/10 border border-sunset/30 text-sunset text-sm rounded-2xl p-4">
            {error}
          </div>
        )}

        <button
          onClick={onPay}
          disabled={submitting}
          className="w-full md:w-auto px-8 h-12 rounded-full bg-ink text-cream font-medium hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] inline-flex items-center justify-center gap-2 group disabled:opacity-50"
        >
          {submitting ? (
            <>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-4 h-4 border-2 border-cream border-t-transparent rounded-full"
              />
              Processing…
            </>
          ) : (
            <>
              Pay {formatMoney(total)} · Confirm booking
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-500" />
            </>
          )}
        </button>
      </div>

      {/* Order summary */}
      <div className="bg-white rounded-3xl border border-ink/10 p-6 h-fit sticky top-24">
        <h4 className="text-xs font-semibold uppercase tracking-widest text-ink/50 mb-4">
          Order summary
        </h4>
        <div className="space-y-3 pb-4 border-b border-ink/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-ink text-cream flex items-center justify-center text-xs font-display font-semibold">
              {selectedFlight.airlineCode}
            </div>
            <div>
              <div className="font-semibold text-sm">{selectedFlight.flightNumber}</div>
              <div className="text-xs text-ink/50">{selectedFlight.aircraft}</div>
            </div>
          </div>
          <div className="text-sm text-ink/70">
            <span className="font-medium text-ink">{selectedFlight.fromAirport.code}</span>
            <span className="mx-2 text-ink/40">→</span>
            <span className="font-medium text-ink">{selectedFlight.toAirport.code}</span>
          </div>
          <div className="text-xs text-ink/50">
            {formatDate(selectedFlight.departureTime)} · {formatTime(selectedFlight.departureTime)} → {formatTime(selectedFlight.arrivalTime)} · {formatDuration(selectedFlight.durationMin)}
          </div>
        </div>
        <div className="py-4 space-y-2 border-b border-ink/10">
          <div className="flex justify-between text-sm">
            <span className="text-ink/60">Seat {selectedSeat.seatNumber} · {selectedSeat.cabinClass}</span>
            <span>{formatMoney(selectedSeat.price)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-ink/60">Passenger</span>
            <span className="text-right">{passenger.name}</span>
          </div>
        </div>
        <div className="pt-4 flex justify-between items-baseline">
          <span className="text-sm text-ink/60">Total to pay</span>
          <span className="font-display text-2xl font-semibold">{formatMoney(total)}</span>
        </div>
      </div>
    </div>
  );
}

function PField({
  label,
  value,
  onChange,
  placeholder,
  className = "",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="text-xs font-semibold uppercase tracking-widest text-ink/50">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1.5 w-full h-14 px-4 rounded-full bg-cream/50 border border-ink/15 focus:border-sky focus:bg-white outline-none transition-all duration-300 ease-[cubic-bezier(0.65,0,0.35,1)]"
      />
    </label>
  );
}
