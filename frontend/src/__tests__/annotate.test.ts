import { describe, expect, it } from "vitest";
import { buildRankingGroups } from "@/lib/annotate";

describe("buildRankingGroups", () => {
  it("builds grouped rankings from ordered items", () => {
    const groups = buildRankingGroups([
      { id: 11, model_id: "m1", content: "a", group: 0 },
      { id: 12, model_id: "m2", content: "b", group: 0 },
      { id: 13, model_id: "m3", content: "c", group: 1 },
    ]);

    expect(groups).toEqual([[11, 12], [13]]);
  });

  it("falls back to single-item groups when group is missing", () => {
    const groups = buildRankingGroups([
      { id: 11, model_id: "m1", content: "a" },
      { id: 12, model_id: "m2", content: "b" },
    ]);

    expect(groups).toEqual([[11], [12]]);
  });
});
