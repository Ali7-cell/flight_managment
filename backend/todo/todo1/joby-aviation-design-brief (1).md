# Joby Aviation — Design Brief (Extracted via Web Scrape)

Scraped from `https://www.jobyaviation.com/` on 2026‑09‑06.
Pages analyzed: Home (`/`), Experience (`/experience`).

---

## 1. Color Palette

| Role | Name | Hex | RGB | Usage on Joby |
|------|------|-----|-----|----------------|
| Primary background | **Cream** | `#F5F4DF` | `245, 244, 223` | Body / page background |
| Primary text | **Ink** | `#0E1620` | `14, 22, 32` | Headlines & body copy on cream |
| Sky accent | **Joby Blue** | `#007AE5` | `0, 122, 229` | Hero backgrounds, key CTAs |
| Deep accent | **Deep Blue** | `#1C3F99` | `28, 63, 153` | Section backgrounds, links |
| Marine accent | **Marine** | `#083E6F` | `8, 62, 111` | Dark navy variant |
| Warm accent | **Sunset** | `#EB6110` | `235, 97, 16` | Hover / highlight color |
| Soft pastel | **Peach** | `#FFD9C9` | `255, 217, 201` | Soft section background |
| Text muted | `rgba(199,197,182,1)` | — | — | Muted caption text on dark sections |

### Pairings used on Joby
- **Cream section** → Ink text, blue accents
- **Joby Blue section** → Cream text
- **Ink (dark) section** → Cream text, blue accents
- **Peach section** → Ink text

---

## 2. Typography

Joby uses **two custom variable fonts**: `jobyDisplay` (headings) and `jobyText` (body), each with a 100–900 weight range. Both are loaded as `woff2` variable fonts.

### Heading scale
| Element | Font | Size | Weight | Letter‑spacing | Line‑height |
|---------|------|------|--------|----------------|-------------|
| H1 (hero) | `jobyDisplay` | `80px` | `550` | `-2.4px` | `80px` (1.0) |
| H2 | `jobyDisplay` | `64px` | `550` | `-1.92px` | `64px` (1.0) |
| H3 | `jobyDisplay` | `48px` | `500` | `-1.44px` | `48px` (1.0) |
| Mega display | `jobyDisplay` | `86px` | `500` | `-3.52px` | `86px` |
| Section label (eyebrow) | `jobyDisplay` | `10px` | `500` | normal | `12px` |

### Body
- `jobyText`, weight 400, comfortable line-height.
- Buttons: Arial fallback at `13.33px`, weight 400, padding `8px 12px`.

### Closest free font alternatives
- **Geist Sans** (already in project) — modern geometric sans, variable 100–900, closest free analog to `jobyDisplay`.
- **Inter** — fallback for body if needed.
- Use **`tracking-tight`** / negative letter-spacing on display sizes to mimic Joby's tight tracking.

---

## 3. Layout & Spacing

- **Full‑bleed hero** (≈ 1080px viewport height on desktop)
- **Alternating cream / dark navy sections** with no gutters between
- **Pill-shaped buttons**: `border-radius: 120px` (or `rounded-full`)
- **Minimal button padding**: `8px 12px` with `13.33px` text
- **Long-form columns** with generous whitespace
- **Tight tracking** on display type (`letter-spacing` from -1.44px to -3.52px)

---

## 4. Animations & Motion (the heart of Joby's feel)

### Keyframes extracted from CSS
```css
@keyframes fadeIn { 0% { opacity: 0 } 100% { opacity: 1 } }

@keyframes translate-out-in-x-1 {
  0%        { opacity: 1; transform: translate(0px); }
  49.99%    { opacity: 0; transform: translate(1rem); }
  50%       { opacity: 0; transform: translate(-1rem); }
  100%      { opacity: 1; transform: translate(0px); }
}

@keyframes translate-out-in-x-2 {
  /* same as above but 2rem shift */
}

@keyframes underline-in-out {
  0%        { transform-origin: 100% center; transform: scaleX(1); }
  49.99%    { transform-origin: 100% center; transform: scaleX(0); }
  50%       { transform-origin: 0% center;  transform: scaleX(0); }
  100%      { transform-origin: 0% center;  transform: scaleX(1); }
}
```

The **underline-in-out** trick is what makes Joby's nav links feel alive — the underline wipes from right→left origin instead of fading.

### Easing curves
- **Primary**: `cubic-bezier(0.65, 0, 0.35, 1)` — smooth in-out
- **Ease-out**: `cubic-bezier(0.33, 1, 0.68, 1)` — slight overshoot
- **Ease-in**: `cubic-bezier(0.35, 0.2, 0, 1)`

### Durations
- **Quick transitions** (color, transform): `0.3s`
- **Entrance animations**: `0.5s – 0.9s`
- **Stagger delays**: `0.105s`, `0.25s`, `0.26s` (for sequenced section reveals)

### Implementation notes
- Use **Framer Motion** with custom cubic-bezier easings
- `whileInView` for scroll-triggered reveals with `once: true, amount: 0.3`
- `staggerChildren` 0.1–0.25s for sequenced section content
- Animated nav link underline that swaps `transform-origin` (right→left) between exit and enter

---

## 5. UI Patterns

- **Sticky transparent navbar** over hero, becomes solid cream/ink on scroll
- **Rotating hero text slides** — hero subtitle cycles through several taglines with fade+slide
- **Large editorial photography** fills full viewport height in hero
- **Footer** on dark navy with cream text, link columns
- **Cookie consent** uses pill buttons (rounded-full) on cream background

---

## 6. Section Inventory (Home)

1. Hero — full-bleed video/image, large display headline, eyebrow label
2. Tech / aircraft showcase — dark section with cinematic visuals
3. Stats block — large numbers (Joby uses count-up on scroll)
4. Partners — logos with hover scale
5. News — editorial cards with hover lift
6. Footer — link columns on dark navy

---

## 7. How this maps to the flight-booking project

| Joby pattern | Flight-booking adaptation |
|--------------|---------------------------|
| Cream + Ink + Joby Blue palette | Same palette, applied to booking UI |
| Large display hero | Hero with integrated flight search |
| Underline-in-out link hover | Used on all nav links & list items |
| FadeIn + translate staggered | Applied to flight cards, search results, section reveals |
| Full-bleed cinematic hero | Hero with cloud/sky imagery, search panel anchored bottom |
| Alternating cream / dark sections | Marketing page alternates cream → ink → cream |
| Pill buttons (rounded-full) | All CTAs use `rounded-full` with cream/ink backgrounds |
| Scroll-triggered reveals | Every section uses `whileInView` with stagger |
