# 🎯 Antigravity Prompt — Skyway Flight Booking Website

> **Reference website (design language):** https://www.jobyaviation.com/
> **Reference design brief:** `./joby-aviation-design-brief.md` (in same folder)
> **Animation files:** `./animation-files/` folder (drop-in CSS + Framer Motion)

---

## 📋 PROJECT BRIEF

Build a flight-booking website called **Skyway** with a fully working backend + frontend. The backend logic, API endpoints, and database schema below are **final and must stay exactly as specified** — do NOT invent new endpoints, do NOT change the request/response shapes. Only the UI/UX is open for design exploration, and that UI/UX must follow the Joby Aviation design language defined in the animation files.

The frontend is a **Next.js 16 App Router** + TypeScript + Tailwind CSS 4 + Framer Motion project. The backend is **Next.js API Routes** + **Prisma ORM with SQLite**.

### Design constraints (NON-NEGOTIABLE)
- **Animation system:** Use the keyframes, Framer Motion variants, easings, and durations from the `./animation-files/` folder. These are extracted from Joby Aviation's actual CSS. Do not replace them with generic Tailwind animations.
- **Easing:** All transitions use `cubic-bezier(0.65, 0, 0.35, 1)` as the primary curve (Joby's signature feel).
- **Colors:** Use the Joby palette defined in `joby-theme.css`:
  - Cream `#F5F4DF` (background)
  - Ink `#0E1620` (text, primary buttons)
  - Joby Blue `#007AE5` (CTAs, links on dark)
  - Deep Blue `#1C3F99` (sections)
  - Sunset `#EB6110` (hover / destructive)
  - Peach `#FFD9C9` (soft accent)
- **Typography:** Variable-weight sans (Inter or Geist), display headings use `letter-spacing: -0.03em` and `line-height: 0.95`.
- **Buttons:** All CTAs are pill-shaped (`border-radius: 9999px` / `rounded-full`), with `0.5s` transition on the Joby easing.
- **Nav links:** Use the `nav-underline` CSS utility (right→left origin wipe, defined in `joby-animations.css`).
- **Layout:** Alternating cream → ink → cream sections, full-bleed hero, sticky transparent navbar that turns solid cream on scroll, sticky footer pushed to bottom with `min-h-screen flex flex-col`.

---

## 🗄️ BACKEND — Prisma Schema (FINAL)

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model Airport {
  code     String   @id // IATA code, e.g. "JFK"
  name     String
  city     String
  country  String
  region   String   // continent / region tag for filtering
  lat      Float
  lng      Float
  timezone String

  departures Flight[] @relation("FromAirport")
  arrivals   Flight[] @relation("ToAirport")
}

model Flight {
  id             String   @id @default(cuid())
  flightNumber   String   @unique // e.g. "SKY-204"
  airline        String
  airlineCode    String // 2-letter ICAO, e.g. "SKY"
  fromCode       String
  toCode         String
  fromAirport    Airport  @relation("FromAirport", fields: [fromCode], references: [code])
  toAirport      Airport  @relation("ToAirport", fields: [toCode], references: [code])
  departureTime  DateTime
  arrivalTime    DateTime
  durationMin    Int
  aircraft       String   // e.g. "Embraer E190"
  totalSeats     Int
  availableSeats Int
  priceEconomy   Float
  priceBusiness  Float
  priceFirst     Float
  status         String   @default("scheduled") // scheduled | delayed | boarding | departed | cancelled
  gate           String?
  createdAt       DateTime @default(now())

  seats    Seat[]
  bookings Booking[]
}

model Seat {
  id          String  @id @default(cuid())
  flightId    String
  flight      Flight  @relation(fields: [flightId], references: [id], onDelete: Cascade)
  seatNumber  String // e.g. "12A"
  cabinClass  String // economy | business | first
  row         Int
  column      String // A | B | C | D | E | F
  isAvailable Boolean @default(true)
  price       Float

  @@unique([flightId, seatNumber])
  @@index([flightId])
}

model Booking {
  id             String   @id @default(cuid())
  reference      String   @unique // human-friendly, e.g. "SKY-AB12CD"
  flightId       String
  flight         Flight   @relation(fields: [flightId], references: [id])
  seatNumber     String
  cabinClass     String
  passengerName  String
  passengerEmail String
  passengerPhone String?
  totalAmount    Float
  currency       String   @default("USD")
  status         String   @default("confirmed") // confirmed | cancelled | completed
  paymentMethod  String?
  paymentStatus  String   @default("paid") // pending | paid | refunded
  createdAt      DateTime @default(now())

  @@index([flightId])
  @@index([passengerEmail])
}
```

After writing the schema, run:
```bash
bun run db:push
```

### Seed data
Seed 20+ real airports (incl. JFK, LAX, SFO, ORD, MIA, SEA, YYZ, LHR, CDG, FRA, AMS, MAD, DXB, IST, SIN, HKG, NRT, ICN, BOM, KHI, SYD) and ~540 flights across 30 routes over the next 14 days. Generate seats per flight using the rules:
- 6-abreast layout: columns `A, B, C, D, E, F`
- First 2 rows = **first class** (4.2× economy price)
- Next 4 rows = **business** (2.6× economy price)
- Remaining rows = **economy** (base price)
- Base price formula: `Math.round((km * 0.09 + 90) * 100) / 100`
- Haversine distance between airports; cruising speed 850 km/h; add 25 min for taxi/landing
- Aircraft by distance: <1500 km → ERJ-190 (24 seats); <4000 km → A320neo (150); <9000 km → 787-9 (216); else A350-900 (254)

The seed script (reference implementation) is at `scripts/seed.ts` in this folder.

---

## 🔌 BACKEND — API Endpoints (FINAL)

All endpoints are **relative paths** (per sandbox Caddy gateway rules). No absolute URLs.

### 1. `GET /api/airports?q=<query>&limit=<n>`
- **Purpose:** Airport autocomplete for the search form.
- **Query params:** `q` (search string, case-insensitive — matches code, city, name, country), `limit` (default 30, max 100).
- **Behavior:** If `q` is empty, return a curated set of popular airports (`JFK, LHR, LAX, DXB, SIN, CDG, HKG, NRT, SYD, KHI`). Boost exact code matches to the top.
- **Response:**
```json
{
  "airports": [
    {
      "code": "JFK",
      "name": "John F. Kennedy International",
      "city": "New York",
      "country": "United States",
      "region": "North America",
      "lat": 40.6413,
      "lng": -73.7781,
      "timezone": "America/New_York"
    }
  ]
}
```

### 2. `GET /api/flights?from=JFK&to=LHR&date=YYYY-MM-DD&limit=50`
- **Purpose:** Search for flights on a given route and date.
- **Query params:** `from`, `to` (IATA codes, **required**), `date` (YYYY-MM-DD, optional — defaults to next 30 days from now), `limit` (default 50, max 200).
- **Behavior:** Filter by `fromCode`, `toCode`, `availableSeats > 0`, and `departureTime` within the date's 24h window (UTC). Order by `departureTime` ascending. Include `fromAirport` and `toAirport` relations.
- **Response:**
```json
{
  "flights": [
    {
      "id": "cmtp...",
      "flightNumber": "SKY-203",
      "airline": "Skyway Air",
      "airlineCode": "SKY",
      "fromCode": "JFK",
      "toCode": "LHR",
      "fromAirport": { ...full Airport object... },
      "toAirport": { ...full Airport object... },
      "departureTime": "2026-09-09T10:30:00.000Z",
      "arrivalTime": "2026-09-09T22:35:00.000Z",
      "durationMin": 425,
      "aircraft": "787-9",
      "totalSeats": 216,
      "availableSeats": 216,
      "priceEconomy": 412,
      "priceBusiness": 1071.2,
      "priceFirst": 1730.4,
      "status": "scheduled",
      "gate": "T2-14",
      "createdAt": "2026-09-06T..."
    }
  ],
  "count": 6
}
```

### 3. `GET /api/flights/[id]/seats`
- **Purpose:** Fetch the full seat map for a flight (for seat selection step).
- **Path param:** `id` = flight row id (cuid).
- **Behavior:** Return the flight (with `fromAirport`, `toAirport`) and all its seats ordered by `[row asc, column asc]`.
- **Response:**
```json
{
  "flight": { ...Flight + fromAirport + toAirport... },
  "seats": [
    {
      "id": "cuid",
      "flightId": "cuid",
      "seatNumber": "7A",
      "cabinClass": "economy",
      "row": 7,
      "column": "A",
      "isAvailable": true,
      "price": 412
    }
  ]
}
```

### 4. `POST /api/booking`
- **Purpose:** Create a new booking. **MUST be a Prisma transaction.**
- **Request body:**
```json
{
  "flightId": "cmtp...",
  "seatNumber": "7A",
  "cabinClass": "economy",
  "passengerName": "Jane Doe",
  "passengerEmail": "jane@email.com",
  "passengerPhone": "+1 555 123 4567", // optional
  "paymentMethod": "card" // card | wallet | paypal
}
```
- **Behavior (transaction):**
  1. Validate flight exists
  2. Validate seat exists for that flight AND `isAvailable === true` (else return 409 Conflict)
  3. Generate a unique reference like `SKY-XXXXX` (5 random chars from `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`)
  4. Create the booking row with `status: "confirmed"`, `paymentStatus: "paid"`, `totalAmount` = `seat.price`
  5. Update the seat: `isAvailable = false`
  6. Decrement the flight's `availableSeats` by 1
  7. Return the created booking
- **Response (201):**
```json
{
  "booking": {
    "id": "cuid",
    "reference": "SKY-F69KH",
    "flightId": "cuid",
    "seatNumber": "7A",
    "cabinClass": "economy",
    "passengerName": "Jane Doe",
    "passengerEmail": "jane@email.com",
    "passengerPhone": "+1 555 123 4567",
    "totalAmount": 589,
    "currency": "USD",
    "status": "confirmed",
    "paymentMethod": "card",
    "paymentStatus": "paid",
    "createdAt": "2026-09-06T..."
  }
}
```
- **Errors:** 400 (missing fields / invalid JSON), 404 (flight or seat not found), 409 (seat already booked).

### 5. `GET /api/booking/[id]`
- **Purpose:** Fetch a booking by its **reference** (e.g. `SKY-F69KH`) or row id.
- **Path param:** `id` — try by `reference` first, fall back to row `id`.
- **Response:** `{ "booking": { ...Booking + flight: { ...Flight + fromAirport + toAirport... } } }`
- **Errors:** 404 if neither matches.

---

## 🧩 FRONTEND — Component Structure

The frontend is a **single visible route** at `/` (per sandbox constraint). All booking flow happens in overlays / sections rendered on the same page, driven by a Zustand store.

### Zustand store (`src/store/booking-store.ts`)
Manages this state machine:
```typescript
type BookingStep =
  | "search"       // default — hero search visible, marketing sections below
  | "results"      // user clicked Search — flight results render under the hero
  | "seats"        // user clicked Select on a flight — full-screen wizard overlay opens
  | "passenger"    // user picked a seat — passenger form step
  | "payment"      // user filled passenger info — payment form step
  | "confirmation";// user paid — boarding pass confirmation
```

Store shape (must match exactly):
```typescript
interface BookingState {
  query: { from: string; to: string; date: string; passengers: number; cabin: "economy" | "business" | "first" };
  flights: Flight[];
  resultsLoading: boolean;
  step: BookingStep;
  selectedFlight: Flight | null;
  seats: Seat[];
  selectedSeat: Seat | null;
  passenger: { name: string; email: string; phone: string };
  payment: { cardName: string; cardNumber: string; expiry: string; cvc: string; method: "card" | "wallet" | "paypal" };
  booking: Booking | null;
  // setters + a reset() that returns to step="search"
}
```

### Page composition (`src/app/page.tsx`)
```
<div className="min-h-screen flex flex-col bg-cream">
  <Navbar />
  <main className="flex-1">
    <Hero />                                    {/* contains SearchForm */}
    {step === "results" && <FlightResults />}  {/* shown after search */}
    <FeaturedRoutes />                          {/* id="routes" */}
    <HowItWorks />                              {/* id="how" */}
    <Stats />                                   {/* id="fleet" */}
    <Partners />
    <NewsSection />                             {/* id="news" */}
  </main>
  <Footer />
  <BookingWizard />                             {/* overlay shown for steps: seats/passenger/payment/confirmation */}
</div>
```

### Required components (with key behaviors)
| Component | Location | Behavior |
|----------|---------|----------|
| `Navbar` | `src/components/site/Navbar.tsx` | Fixed transparent → solid cream on scroll. Logo + 5 nav links (with `nav-underline` hover). "Sign in" link + "Book a flight" pill button on right. Mobile hamburger menu (slide-down). |
| `Hero` | `src/components/site/Hero.tsx` | Full-bleed sky gradient (`#7CC0F5 → #007AE5 → #1C3F99`). Animated clouds (3 blur blobs drifting on `easeInOut`). Floating plane with contrail. Rotating headline every 3.8s ("Skip traffic. Time to fly." variants, AnimatePresence fade+slide). Embeds `SearchForm`. Stats strip with 4 numbers. |
| `SearchForm` | `src/components/site/SearchForm.tsx` | White pill-shaped card. Fields: From (autocomplete), To (autocomplete), Date, Passengers dropdown, Cabin dropdown, "Search" pill button. Airport autocomplete: debounced 180ms, shows code + city + country in dropdown. Hover/focus use Joby easing. |
| `FlightResults` | `src/components/booking/FlightResults.tsx` | Renders below hero after search. Header with route summary ("JFK → LHR"), "New search" link. List of `FlightCard`s with staggered fadeIn (0.05s delay per card). Empty state + loading state with animated plane. |
| `FlightCard` | `src/components/booking/FlightCard.tsx` | White rounded-2xl card with hover lift (y: -6) and border color change to sky blue. Left: airline block (logo + name + flight number + aircraft). Center: dep time → duration line with plane icon → arr time. Right: price + "Select" pill button. |
| `BookingWizard` | `src/components/booking/BookingWizard.tsx` | Full-screen cream overlay (`fixed inset-0 z-50`). Sticky top bar with Back button + step indicator (1/4 → 4/4 with check icons for past steps) + close button. AnimatePresence between steps with y: ±24 fade. |
| `SeatSelection` | `src/components/booking/SeatSelection.tsx` | Plane-shape seat map. Cabin switcher (Economy/Business/First pill tabs, disabled if 0 seats). Rows × A-F grid with aisle gap in the middle. Available seat = white border, hover = sky. Selected = sky bg with check. Taken = gray, disabled. Sticky right sidebar with selection summary + price + Continue button. |
| `PassengerForm` | `src/components/booking/PassengerForm.tsx` | Name, Email, Phone fields with leading icons. Validation: name > 1 char, valid email regex. Privacy note. Continue to payment button (disabled until valid). |
| `PaymentForm` | `src/components/booking/PaymentForm.tsx` | Payment method tabs (Card / Wallet / PayPal, 3 columns). Card fields: name, number, expiry, cvc. Order summary sidebar with flight info + seat + total. "Pay $X · Confirm booking" button with spinner while submitting. Error toast on failure. |
| `Confirmation` | `src/components/booking/Confirmation.tsx` | Animated check (scale-in). "You're cleared for takeoff." heading. Boarding pass card with perforation + barcode + reference. Download + Book-another buttons. |
| `FeaturedRoutes` | `src/components/site/FeaturedRoutes.tsx` | 6 popular routes as gradient cards (Joby blue → deep blue, sunset → dark, peach → sunset, etc.). Each card: route code pair, city names, from price, duration. Hover: y: -6, plane illustration wobbles. Click → quick search. |
| `HowItWorks` | `src/components/booking/HowItWorks.tsx` (or site/) | Dark ink section. 3 numbered steps with circular icon containers, connector lines on desktop, staggered fadeIn. |
| `Stats` | `src/components/site/Stats.tsx` | 4 big numbers with count-up animation on scroll (1.6s, cubic ease-out). |
| `Partners` | `src/components/site/Partners.tsx` | Auto-scrolling marquee with edge fades. 10 partner names. Animation: `animate-marquee` 40s linear infinite. |
| `NewsSection` | `src/components/site/NewsSection.tsx` | 3 editorial cards with gradient art blocks (subtle ken-burns inside), category chip, date, headline, excerpt. Hover lift. |
| `Footer` | `src/components/site/Footer.tsx` | Dark ink section. Newsletter form + 4 link columns + social icons + bottom legal bar. |

### Required utilities (`src/lib/format.ts`)
```typescript
formatMoney(value, currency = "USD")   // Intl.NumberFormat, no decimals
formatTime(iso)                         // "10:35 AM"
formatDate(iso)                         // "Mon, Sep 10"
formatDateLong(iso)                     // "September 10, 2026"
formatDuration(min)                     // "5h 25m"
cabinLabel(cabin)                       // "First" | "Business" | "Economy"
priceForCabin(flight, cabin)            // picks the right price field
seatsToGrid(seats)                      // returns [{ row, cells: [Seat|null × 6] }]
countByCabin(seats)                     // { totals, available } per cabin
```

---

## 🎬 ANIMATION INSTRUCTIONS (NON-NEGOTIABLE)

**Use the animation files in `./animation-files/` — they were extracted from Joby Aviation's actual CSS.**

### Files to drop into your project:
1. **`./animation-files/joby-theme.css`** → import at top of your global stylesheet. Contains the color CSS variables and easing/duration tokens.
2. **`./animation-files/joby-animations.css`** → import after `joby-theme.css`. Contains all keyframes + the `nav-underline` utility + `paper-grain` texture + marquee + ken-burns.
3. **`./animation-files/joby-motion.ts`** → import in any Framer Motion component. Contains ready-to-use variants for `fadeUp`, `fadeIn`, `staggerContainer`, `staggerItem`, `slideInLeft`, `slideInRight`, `underlineInOut`, `marqueeVariants`, and the shared `JOB_EASE` constant.
4. **`./animation-files/joby-typography.css`** → contains the `.font-display` utility + heading scale (H1 80px / H2 64px / H3 48px with tracking).

### Rules for using these animations:
- **All Framer Motion transitions** use `ease: JOB_EASE` (the cubic-bezier constant).
- **Scroll reveals** use `whileInView` with `viewport={{ once: true, amount: 0.3 }}` and the `fadeUp` variant (duration 0.6s).
- **Staggered lists** use `staggerContainer` with `staggerChildren: 0.08` (for cards) or `0.1` (for stat numbers).
- **Hero headline rotation** uses `<AnimatePresence mode="wait">` with `slideInLeft` variants on a 3.8s timer.
- **Nav links + footer links + bottom buttons** use the `nav-underline` CSS utility (NOT a Framer Motion variant) — the wipe-from-right-origin-then-into-left-origin is the Joby signature.
- **Hero plane** uses the `kenburns` keyframe for slow zoom + a separate Framer Motion loop for tilt (`rotate: [-3, 4, -3]` over 4s).
- **Partner logos** use the `marquee` keyframe (40s linear infinite) — duplicate the list to make it seamless.
- **Buttons** use Tailwind `transition-all duration-500 ease-[cubic-bezier(0.65,0,0.35,1)]` for hover state changes (color, transform).
- **Stats numbers** use a custom `CountUp` component (requestAnimationFrame) with cubic ease-out over 1.6s, triggered by `useInView`.
- **Page transitions between booking steps** use `<AnimatePresence mode="wait">` with `initial={{ opacity: 0, y: 24 }}` / `animate={{ opacity: 1, y: 0 }}` / `exit={{ opacity: 0, y: -24 }}` — duration 0.45s.
- **Card hovers** use `whileHover={{ y: -6 }}` with duration 0.5s on `JOB_EASE`.
- **Modal/popover dropdowns** (airport autocomplete, passengers, cabin) use `<AnimatePresence>` with `initial={{ opacity: 0, y: -8 }}` / `animate={{ opacity: 1, y: 0 }}` / `exit={{ opacity: 0, y: -8 }}` — duration 0.25s.

### DO NOT:
- ❌ Use Tailwind's default `animate-pulse`, `animate-bounce`, `animate-spin` for UI chrome (only for loading spinners).
- ❌ Use linear easing for organic UI — always `JOB_EASE`.
- ❌ Use default `ease-out` from Framer Motion — replace with `JOB_EASE`.
- ❌ Skip the `nav-underline` utility on links — it's the most recognizable Joby micro-interaction.
- ❌ Use blue (`#3B82F6` Tailwind blue) anywhere — use Joby Blue `#007AE5`.

---

## 🚦 ACCEPTANCE CRITERIA

The build is complete when ALL of these pass:

1. `bun run lint` exits 0 (no errors, no warnings).
2. Home page (`/`) renders with: navbar, hero with rotating headline + search form, then 6 marketing sections (routes, how, fleet/stats, partners, news), then footer.
3. Search "JFK → LHR" returns ≥ 1 flight.
4. Clicking "Select" on a flight opens the booking wizard overlay with a live seat map (6-abreast, cabin switcher).
5. Picking a seat shows the price in a sticky sidebar and enables "Continue".
6. After passenger info + payment, `POST /api/booking` returns 201 with a `SKY-XXXXX` reference.
7. Confirmation screen shows a boarding pass with the reference + barcode.
8. Mobile (390×844): navbar collapses to hamburger, hero is full-bleed, all sections stack.
9. Every animation uses `JOB_EASE`. Every link uses `nav-underline`. Every button is `rounded-full`.

---

## 📁 FILE LAYOUT (target)

```
prisma/
  schema.prisma
scripts/
  seed.ts
src/
  app/
    layout.tsx          # Geist Sans, metadata
    page.tsx            # composition above
    globals.css         # imports joby-theme + joby-animations + tailwind
    api/
      airports/route.ts
      flights/route.ts
      flights/[id]/seats/route.ts
      booking/route.ts
      booking/[id]/route.ts
  components/
    site/
      Navbar.tsx
      Hero.tsx
      SearchForm.tsx
      FeaturedRoutes.tsx
      HowItWorks.tsx
      Stats.tsx
      Partners.tsx
      NewsSection.tsx
      Footer.tsx
    booking/
      FlightCard.tsx
      FlightResults.tsx
      SeatSelection.tsx
      PassengerForm.tsx
      PaymentForm.tsx
      Confirmation.tsx
      BookingWizard.tsx
  store/
    booking-store.ts    # Zustand
  lib/
    db.ts               # Prisma client singleton
    format.ts           # formatters + seatsToGrid
    types.ts            # Airport, Flight, Seat, Booking, SearchQuery, CabinClass
    motion.ts           # imports from animation-files/joby-motion.ts (or copy)
```

---

## 🎁 DONE = ALL OF THE ABOVE + RUNS IN BROWSER

Start with the Prisma schema + seed, then API routes (test each with curl), then the store + format utilities, then the components in dependency order (Navbar → Hero → SearchForm → FlightResults → FlightCard → SeatSelection → PassengerForm → PaymentForm → Confirmation → BookingWizard → page.tsx composition).

**Reference:** Open https://www.jobyaviation.com/ in a browser alongside your build. Match its feel — the slow easing, the pill buttons, the cream/ink contrast, the tight-tracked headlines, the underline-wipe on links. That's the target.
