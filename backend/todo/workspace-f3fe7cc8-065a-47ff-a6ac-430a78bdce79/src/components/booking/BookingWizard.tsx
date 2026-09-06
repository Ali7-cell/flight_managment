"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X, ArrowLeft, Check } from "lucide-react";
import { useBookingStore } from "@/store/booking-store";
import { SeatSelection } from "./SeatSelection";
import { PassengerForm } from "./PassengerForm";
import { PaymentForm } from "./PaymentForm";
import { Confirmation } from "./Confirmation";
import { cn } from "@/lib/utils";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const STEPS = [
  { key: "seats",      label: "Seat",     number: 1 },
  { key: "passenger",  label: "Passenger", number: 2 },
  { key: "payment",    label: "Payment",   number: 3 },
  { key: "confirmation", label: "Done",    number: 4 },
] as const;

export function BookingWizard() {
  const { step, setStep, reset } = useBookingStore();

  const isOpen = ["seats", "passenger", "payment", "confirmation"].includes(step);
  if (!isOpen) return null;

  const currentIdx = STEPS.findIndex((s) => s.key === step);
  const current = STEPS[currentIdx];
  const prev = currentIdx > 0 ? STEPS[currentIdx - 1] : null;

  const onBack = () => {
    if (step === "seats") {
      // Close the wizard, go back to results
      setStep("results");
      // Scroll to results
      setTimeout(() => {
        document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
      }, 50);
    } else if (prev) {
      setStep(prev.key as any);
    }
  };

  const onClose = () => {
    setStep("results");
    setTimeout(() => {
      document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4, ease: JOB_EASE }}
          className="fixed inset-0 z-50 bg-cream overflow-y-auto scrollbar-thin"
        >
          {/* Sticky top bar */}
          <motion.header
            initial={{ y: -40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: JOB_EASE }}
            className="sticky top-0 z-20 bg-cream/90 backdrop-blur-md border-b border-ink/10"
          >
            <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 md:h-20 flex items-center justify-between">
              <div className="flex items-center gap-4 md:gap-8">
                <button
                  onClick={onBack}
                  className="inline-flex items-center gap-1.5 text-sm text-ink/70 hover:text-ink transition-colors nav-underline"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>

                {/* Step indicator */}
                <div className="hidden md:flex items-center gap-2">
                  {STEPS.map((s, i) => {
                    const isPast = i < currentIdx;
                    const isCurrent = i === currentIdx;
                    return (
                      <div key={s.key} className="flex items-center gap-2">
                        <div
                          className={cn(
                            "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]",
                            isCurrent
                              ? "bg-ink text-cream"
                              : isPast
                              ? "bg-sky/10 text-sky"
                              : "text-ink/40"
                          )}
                        >
                          <div
                            className={cn(
                              "w-5 h-5 rounded-full flex items-center justify-center text-xs font-semibold",
                              isCurrent ? "bg-cream text-ink" : isPast ? "bg-sky text-white" : "bg-ink/15"
                            )}
                          >
                            {isPast ? <Check className="w-3 h-3" /> : s.number}
                          </div>
                          <span className="font-medium">{s.label}</span>
                        </div>
                        {i < STEPS.length - 1 && (
                          <div className={cn("w-6 h-[1px]", isPast ? "bg-sky" : "bg-ink/15")} />
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Mobile compact step indicator */}
                <div className="md:hidden text-sm text-ink/60">
                  Step {current.number} of {STEPS.length}
                </div>
              </div>

              <button
                onClick={onClose}
                className="w-10 h-10 rounded-full bg-cream/60 hover:bg-cream border border-ink/10 flex items-center justify-center transition-colors"
                aria-label="Close booking"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </motion.header>

          {/* Content with AnimatePresence between steps */}
          <div className="max-w-7xl mx-auto px-6 lg:px-8 py-12 md:py-16">
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -24 }}
                transition={{ duration: 0.45, ease: JOB_EASE }}
              >
                {step === "seats" && <SeatSelection />}
                {step === "passenger" && <PassengerForm />}
                {step === "payment" && <PaymentForm />}
                {step === "confirmation" && <Confirmation />}
              </motion.div>
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
