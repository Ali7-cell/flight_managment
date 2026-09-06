"use client";

import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, User, Mail, Phone, Check } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

export function PassengerForm() {
  const { passenger, setPassenger, setStep } = useBookingStore();

  const valid = passenger.name.trim().length > 1 && /.+@.+\..+/.test(passenger.email);

  const onContinue = () => {
    if (valid) setStep("payment");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h3 className="font-display text-2xl md:text-3xl font-semibold tracking-tight">
          Passenger details
        </h3>
        <p className="text-ink/60 text-sm mt-1">
          We&apos;ll send your boarding pass and confirmation to this email.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field
          label="Full name"
          icon={User}
          value={passenger.name}
          onChange={(v) => setPassenger({ name: v })}
          placeholder="Jane Doe"
          required
        />
        <Field
          label="Email"
          icon={Mail}
          type="email"
          value={passenger.email}
          onChange={(v) => setPassenger({ email: v })}
          placeholder="jane@email.com"
          required
        />
        <Field
          label="Phone (optional)"
          icon={Phone}
          type="tel"
          value={passenger.phone}
          onChange={(v) => setPassenger({ phone: v })}
          placeholder="+1 555 123 4567"
          className="md:col-span-2"
        />
      </div>

      <div className="bg-cream/40 rounded-2xl p-5 border border-ink/10 text-sm text-ink/70 flex items-start gap-3">
        <Check className="w-4 h-4 text-sky mt-0.5 shrink-0" />
        <p>
          Your information is encrypted in transit and at rest. We&apos;ll only use it to send
          your boarding pass and flight updates.
        </p>
      </div>

      <button
        onClick={onContinue}
        disabled={!valid}
        className="w-full md:w-auto px-8 h-12 rounded-full bg-ink text-cream font-medium hover:bg-sky transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] inline-flex items-center justify-center gap-2 group disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Continue to payment
        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-500" />
      </button>
    </div>
  );
}

function Field({
  label,
  icon: Icon,
  value,
  onChange,
  placeholder,
  type = "text",
  required,
  className = "",
}: {
  label: string;
  icon: any;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  type?: string;
  required?: boolean;
  className?: string;
}) {
  return (
    <motion.label
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: JOB_EASE }}
      className={`block ${className}`}
    >
      <span className="text-xs font-semibold uppercase tracking-widest text-ink/50">
        {label}{required && <span className="text-sunset ml-0.5">*</span>}
      </span>
      <div className="relative mt-1.5">
        <Icon className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-ink/40" />
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          required={required}
          className="w-full h-14 pl-11 pr-4 rounded-full bg-cream/50 border border-ink/15 focus:border-sky focus:bg-white outline-none transition-all duration-300 ease-[cubic-bezier(0.65,0,0.35,1)]"
        />
      </div>
    </motion.label>
  );
}
