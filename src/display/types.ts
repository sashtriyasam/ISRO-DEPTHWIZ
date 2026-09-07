export type ExaggerationLevel = 1 | 2 | 5 | 10;

export const EXAGGERATION_LEVELS: ExaggerationLevel[] = [1, 2, 5, 10];

export const DEFAULT_EXAGGERATION: ExaggerationLevel = 1;

export const EXAGGERATION_LABELS: Record<ExaggerationLevel, string> = {
  1: "1x",
  2: "2x",
  5: "5x",
  10: "10x",
};

export function isValidExaggeration(value: number): value is ExaggerationLevel {
  return EXAGGERATION_LEVELS.includes(value as ExaggerationLevel);
}

/**
 * Target visible relief as a fraction of horizontal extent. The viewer maps
 * non-georeferenced pixels 1:1 to world units, so a few metres of relief
 * over hundreds of pixels is legitimately invisible at 1x. Auto-fit picks
 * the smallest level reaching this ratio; it only sets the display
 * control's initial value and never modifies scientific data.
 */
export const AUTO_FIT_RELIEF_FRACTION = 0.1;

export function suggestExaggeration(
  grid: ArrayLike<number>,
  width: number,
  height: number,
): ExaggerationLevel {
  const horizontal = Math.max(width, height);
  if (!(horizontal > 0)) {
    return 1;
  }
  let min = Infinity;
  let max = -Infinity;
  let finite = 0;
  for (let i = 0; i < grid.length; i++) {
    const v = grid[i];
    if (typeof v === "number" && Number.isFinite(v)) {
      finite++;
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  if (finite === 0) {
    return 1;
  }
  const relief = max - min;
  if (!(relief > 0)) {
    return 1;
  }
  for (const level of EXAGGERATION_LEVELS) {
    if ((relief * level) / horizontal >= AUTO_FIT_RELIEF_FRACTION) {
      return level;
    }
  }
  return EXAGGERATION_LEVELS[EXAGGERATION_LEVELS.length - 1];
}

export function applyHeightExaggeration(
  sourceVertices: Float32Array,
  verticalScale: number
): Float32Array {
  const result = new Float32Array(sourceVertices.length);
  for (let i = 0; i < sourceVertices.length; i += 3) {
    result[i] = sourceVertices[i];
    result[i + 1] = sourceVertices[i + 1] * verticalScale;
    result[i + 2] = sourceVertices[i + 2];
  }
  return result;
}
