import { describe, expect, it } from "vitest";
import { formatDuration, formatPercent, truncate } from "@/lib/format";

describe("format helpers", () => {
  it("formats percentages", () => {
    expect(formatPercent(0.123)).toBe("12.3%");
    expect(formatPercent(null)).toBe("--");
  });

  it("formats durations", () => {
    expect(formatDuration(880)).toBe("880 ms");
    expect(formatDuration(2500)).toBe("2.5 s");
  });

  it("truncates long text", () => {
    expect(truncate("hello", 10)).toBe("hello");
    expect(truncate("abcdefghijklmnopqrstuvwxyz", 5)).toBe("abcde…");
  });
});
