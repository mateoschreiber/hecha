import { describe, expect, it } from "vitest";

import { formatDate } from "./lib";

describe("formatDate", () => {
  it("renders source dates for Paraguay", () => {
    expect(formatDate("2021-09-01")).toContain("2021");
  });
});
