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

export function fmtBytes(byteLength) {
  if (!Number.isFinite(byteLength) || byteLength <= 0) {
    return "-";
  }

  const units = ["B", "KB", "MB", "GB"];
  let size = byteLength;
  let index = 0;

  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }

  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}
