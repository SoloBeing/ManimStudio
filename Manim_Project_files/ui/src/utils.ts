/** A render output that should be shown in an <img>, not a <video>.
 *  GIFs animate fine in an <img> and never play in a <video> element. */
export function isImagePath(path: string): boolean {
  return /\.(png|gif|jpe?g)$/.test(path.toLowerCase());
}

/** Prefix a log message with a [HH:MM:SS] timestamp, matching the format the
 *  backend applies to build-log lines, so client-side messages line up. */
export function stamp(msg: string): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `[${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}] ${msg}`;
}
