import { describe, expect, it } from "vitest";
import { formatArea, googleMapsUrl, matchesArea } from "./formatters";

describe("asset formatters", () => {
  it("formats area as rai:ngan:square wah", () => {
    expect(formatArea({ rai: "0", ngan: "1", square_wah: "20" })).toBe(
      "0:1:20",
    );
    expect(formatArea({})).toBe("0:0:0");
  });

  it("creates a safe Google Maps link", () => {
    expect(googleMapsUrl("13.8,100.4")).toBe(
      "https://www.google.com/maps?q=13.8%2C100.4",
    );
    expect(googleMapsUrl("")).toBe("");
  });

  it("matches all configured area conditions", () => {
    const filters = {
      raiCondition: "eq",
      raiValue: "0",
      nganCondition: "gt",
      nganValue: "0",
      squareWahCondition: "lt",
      squareWahValue: "30",
    };
    expect(
      matchesArea({ rai: "0", ngan: "1", square_wah: "20" }, filters),
    ).toBe(true);
    expect(
      matchesArea({ rai: "0", ngan: "0", square_wah: "20" }, filters),
    ).toBe(false);
  });
});
