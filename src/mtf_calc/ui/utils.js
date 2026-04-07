export function fmtNum(value) {
  if (!Number.isFinite(value)) {
    return "n/a";
  }

  if (Math.abs(value) < 0.001 && value !== 0) {
    return value.toExponential(2);
  }

  if (Math.abs(value) >= 10000) {
    return value.toExponential(2);
  }

  return value.toFixed(4);
}

export function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}
