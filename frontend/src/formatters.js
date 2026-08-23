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
  return `${asset.rai || 0}:${asset.ngan || 0}:${asset.square_wah || 0}`;
}

export function googleMapsUrl(location) {
  const coordinate = String(location || "").trim();
  return coordinate
    ? `https://www.google.com/maps?q=${encodeURIComponent(coordinate)}`
    : "";
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
