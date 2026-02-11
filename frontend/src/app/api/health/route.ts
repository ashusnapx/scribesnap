import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${backendUrl}/health`, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Backend health check failed: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      {
        status: "unhealthy",
        error: error instanceof Error ? error.message : "Connect failed",
      },
      { status: 503 },
    );
  }
}
