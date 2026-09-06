"use client";

import { Navbar } from "@/components/site/Navbar";
import { Hero } from "@/components/site/Hero";
import { FeaturedRoutes } from "@/components/site/FeaturedRoutes";
import { HowItWorks } from "@/components/site/HowItWorks";
import { Stats } from "@/components/site/Stats";
import { Partners } from "@/components/site/Partners";
import { NewsSection } from "@/components/site/NewsSection";
import { Footer } from "@/components/site/Footer";
import { FlightResults } from "@/components/booking/FlightResults";
import { BookingWizard } from "@/components/booking/BookingWizard";
import { useBookingStore } from "@/store/booking-store";

export default function Home() {
  const { step } = useBookingStore();

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Navbar />

      <main className="flex-1">
        {/* Hero is always visible — it contains the search form */}
        <Hero />

        {/* When the user has searched, render the results section right after the hero */}
        {step === "results" && <FlightResults />}

        {/* Marketing sections are always visible below — scrollable for context */}
        <div id="experience" className="scroll-mt-20">
          <FeaturedRoutes />
        </div>
        <HowItWorks />
        <Stats />
        <Partners />
        <NewsSection />
      </main>

      <Footer />

      {/* Booking wizard overlay (seats → passenger → payment → confirmation) */}
      <BookingWizard />
    </div>
  );
}
