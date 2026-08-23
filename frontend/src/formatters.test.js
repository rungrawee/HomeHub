import { describe, expect, it } from "vitest";
import {
  calculateDiscountPercent,
  formatArea,
  formatAuctionDate,
  googleMapsUrl,
  matchesArea,
} from "./formatters";

describe("asset formatters", () => {
  it("calculates a discount only when final price is lower", () => {
    expect(calculateDiscountPercent("1500000", "1350000")).toBe(10);
    expect(calculateDiscountPercent("1500000", "1500000")).toBeNull();
    expect(calculateDiscountPercent("0", "0")).toBeNull();
  });

  it("converts ngan to square wah and hides zero rai", () => {
    expect(formatArea({ rai: "0", ngan: "1", square_wah: "20" })).toBe(
      "120 ตร.ว.",
    );
    expect(formatArea({ rai: "0", ngan: "0", square_wah: "27" })).toBe(
      "27 ตร.ว.",
    );
  });

  it("shows rai followed by total square wah", () => {
    expect(formatArea({ rai: "1", ngan: "1", square_wah: "20" })).toBe(
      "1 ไร่ 120 ตร.ว.",
    );
    expect(formatArea({ rai: "4", ngan: "3", square_wah: "30" })).toBe(
      "4 ไร่ 330 ตร.ว.",
    );
    expect(formatArea({})).toBe("0 ตร.ว.");
  });

  it("creates a safe Google Maps link", () => {
    expect(googleMapsUrl("13.8,100.4")).toBe(
      "https://www.google.com/maps?q=13.8%2C100.4",
    );
    expect(googleMapsUrl("")).toBe("");
  });

  it("formats the next auction date in Thai", () => {
    expect(formatAuctionDate("2026-09-10")).toContain("10 กันยายน");
    expect(formatAuctionDate(null)).toBe("ยังไม่มีวันประมูลถัดไป");
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
