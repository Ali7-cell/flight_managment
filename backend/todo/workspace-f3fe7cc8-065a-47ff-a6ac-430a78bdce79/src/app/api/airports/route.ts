import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

// GET /api/airports?q=<query>&limit=<n>
// Returns airports matching the query (by code, city, name, country).
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const q = (url.searchParams.get("q") || "").trim().toUpperCase();
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "30", 10), 100);

  if (!q) {
    // No query — return popular airports (sample of major hubs)
    const all = await db.airport.findMany({
      where: { code: { in: ["JFK", "LHR", "LAX", "DXB", "SIN", "CDG", "HKG", "NRT", "SYD", "KHI"] } },
      orderBy: { city: "asc" },
      take: 30,
    });
    return NextResponse.json({ airports: all });
  }

  const airports = await db.airport.findMany({
    where: {
      OR: [
        { code: { startsWith: q } },
        { city: { contains: q } },
        { name: { contains: q } },
        { country: { contains: q } },
      ],
    },
    orderBy: [{ code: "asc" }, { city: "asc" }],
    take: limit,
  });

  // Boost exact code match to the top
  airports.sort((a, b) => {
    if (a.code === q) return -1;
    if (b.code === q) return 1;
    if (a.code.startsWith(q) && !b.code.startsWith(q)) return -1;
    if (!a.code.startsWith(q) && b.code.startsWith(q)) return 1;
    return 0;
  });

  return NextResponse.json({ airports });
}
