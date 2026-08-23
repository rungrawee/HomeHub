export function formatPrice(value) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("th-TH", {
    style: "currency",
    currency: "THB",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0);
}

export function formatArea(asset) {
  const rai = Number(asset.rai || 0);
  const ngan = Number(asset.ngan || 0);
  const squareWah = Number(asset.square_wah || 0);
  const safeRai = Number.isFinite(rai) ? rai : 0;
  const totalSquareWah =
    (Number.isFinite(ngan) ? ngan : 0) * 100 +
    (Number.isFinite(squareWah) ? squareWah : 0);
  const numberFormat = new Intl.NumberFormat("th-TH", {
    maximumFractionDigits: 2,
  });
  const parts = [];

  if (safeRai > 0) parts.push(`${numberFormat.format(safeRai)} ไร่`);
  if (totalSquareWah > 0 || parts.length === 0) {
    parts.push(`${numberFormat.format(totalSquareWah)} ตร.ว.`);
  }
  return parts.join(" ");
}

export function googleMapsUrl(location) {
  const coordinate = String(location || "").trim();
  return coordinate
    ? `https://www.google.com/maps?q=${encodeURIComponent(coordinate)}`
    : "";
}

export function formatAuctionDate(value) {
  if (!value) return "ยังไม่มีวันประมูลถัดไป";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "ยังไม่มีวันประมูลถัดไป";
  return new Intl.DateTimeFormat("th-TH", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

function compare(actual, condition, expected) {
  if (expected === "") return true;
  const left = Number(actual || 0);
  const right = Number(expected);
  if (!Number.isFinite(right)) return true;
  if (condition === "gt") return left > right;
  if (condition === "lt") return left < right;
  return left === right;
}

export function matchesArea(asset, filters) {
  return (
    compare(asset.rai, filters.raiCondition, filters.raiValue) &&
    compare(asset.ngan, filters.nganCondition, filters.nganValue) &&
    compare(
      asset.square_wah,
      filters.squareWahCondition,
      filters.squareWahValue,
    )
  );
}
