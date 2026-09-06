import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

// GET /api/flights?from=JFK&to=LHR&date=2026-09-10&cabin=economy&limit=50
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const from = (url.searchParams.get("from") || "").toUpperCase();
  const to = (url.searchParams.get("to") || "").toUpperCase();
  const dateStr = url.searchParams.get("date"); // YYYY-MM-DD
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "50", 10), 200);

  if (!from || !to) {
    return NextResponse.json(
      { error: "Both `from` and `to` airport codes are required." },
      { status: 400 }
    );
  }

  // Build date range
  let start: Date | undefined;
  let end: Date | undefined;
  if (dateStr) {
    const d = new Date(dateStr + "T00:00:00Z");
    if (!isNaN(d.getTime())) {
      start = d;
      end = new Date(d.getTime() + 24 * 60 * 60 * 1000);
    }
  }

  const where: any = {
    fromCode: from,
    toCode: to,
    availableSeats: { gt: 0 },
  };
  if (start && end) {
    where.departureTime = { gte: start, lt: end };
  } else {
    // Default: next 30 days from now
    const now = new Date();
    where.departureTime = { gte: now };
  }

  const flights = await db.flight.findMany({
    where,
    orderBy: { departureTime: "asc" },
    take: limit,
    include: { fromAirport: true, toAirport: true },
  });

  return NextResponse.json({ flights, count: flights.length });
}
