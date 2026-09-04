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
