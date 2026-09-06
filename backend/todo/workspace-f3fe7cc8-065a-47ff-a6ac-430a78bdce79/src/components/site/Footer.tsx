"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { Plane, ArrowRight, Twitter, Instagram, Linkedin, Youtube } from "lucide-react";

const JOB_EASE = [0.65, 0, 0.35, 1] as const;

const COLUMNS = [
  {
    title: "Fly",
    links: ["Search flights", "Popular routes", "Group bookings", "Gift cards", "Flight status"],
  },
  {
    title: "Experience",
    links: ["First class", "Business", "Economy", "Lounges", "Skyway Rewards"],
  },
  {
    title: "Company",
    links: ["About us", "Careers", "Press", "Sustainability", "Investors"],
  },
  {
    title: "Support",
    links: ["Help center", "Contact us", "Manage booking", "Refunds", "Travel docs"],
  },
];

export function Footer() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setSent(true);
    setEmail("");
    setTimeout(() => setSent(false), 3000);
  };

  return (
    <footer className="bg-ink text-cream pt-20 pb-10 mt-auto">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Newsletter */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: JOB_EASE }}
          className="grid grid-cols-1 md:grid-cols-2 gap-8 pb-16 border-b border-cream/15"
        >
          <div>
            <h3 className="font-display text-3xl md:text-4xl font-semibold tracking-tight">
              Stories from the sky, in your inbox.
            </h3>
            <p className="mt-3 text-cream/60 max-w-md">
              New routes, secret deals, and the occasional travel tip. No spam — we promise.
            </p>
          </div>
          <form onSubmit={onSubmit} className="flex items-center gap-2 md:justify-end">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@email.com"
              className="flex-1 md:max-w-xs h-12 px-5 rounded-full bg-cream/10 border border-cream/15 placeholder:text-cream/40 text-cream focus:border-sky outline-none transition-colors"
            />
            <button
              type="submit"
              className="h-12 px-6 rounded-full bg-cream text-ink font-medium hover:bg-sky hover:text-cream transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)] flex items-center gap-2"
            >
              {sent ? "Subscribed" : "Subscribe"}
              {!sent && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>
        </motion.div>

        {/* Link columns */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 py-16">
          <div className="col-span-2">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-9 h-9 rounded-full bg-cream text-ink flex items-center justify-center">
                <Plane className="w-4 h-4 -rotate-45" />
              </div>
              <span className="font-display text-2xl font-semibold tracking-tight">Skyway</span>
            </div>
            <p className="text-sm text-cream/60 max-w-xs">
              A next-generation flight booking experience. Built for travellers who value time, design, and a smooth ride.
            </p>
            <div className="flex items-center gap-3 mt-6">
              {[Twitter, Instagram, Linkedin, Youtube].map((Icon, i) => (
                <a
                  key={i}
                  href="#"
                  className="w-9 h-9 rounded-full border border-cream/20 hover:border-sky hover:bg-sky/10 transition-colors duration-500 flex items-center justify-center"
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {COLUMNS.map((col, i) => (
            <motion.div
              key={col.title}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.5, ease: JOB_EASE, delay: i * 0.05 }}
            >
              <div className="text-xs font-semibold uppercase tracking-widest text-cream/40 mb-4">
                {col.title}
              </div>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="nav-underline text-sm text-cream/80 hover:text-cream transition-colors"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="border-t border-cream/15 pt-8 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-cream/50">
          <div>© 2026 Skyway Air, Inc. All rights reserved.</div>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-cream transition-colors">Privacy</a>
            <a href="#" className="hover:text-cream transition-colors">Terms</a>
            <a href="#" className="hover:text-cream transition-colors">Cookies</a>
            <a href="#" className="hover:text-cream transition-colors">Accessibility</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
