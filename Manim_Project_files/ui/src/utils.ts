/** A render output that should be shown in an <img>, not a <video>.
 *  GIFs animate fine in an <img> and never play in a <video> element. */
export function isImagePath(path: string): boolean {
  return /\.(png|gif|jpe?g)$/.test(path.toLowerCase());
}
