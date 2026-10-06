import type { SceneArtifact } from "../types/scene";

/**
 * Attach the RGB texture the backend wrote beside the staged input.
 *
 * The texture holds the same 8-bit pixels the depth model saw (band order
 * and 16-bit stretch applied), so it drapes exactly over the mesh UVs.
 * Without a desktop host, a texture path or image decoding support the
 * artifact is returned unchanged: the RGB layer simply stays unavailable.
 */
export async function attachStagedTexture(artifact: SceneArtifact): Promise<SceneArtifact> {
  const path = artifact.metadata.texturePath;
  const host = typeof window !== "undefined" ? window.depthwizard : undefined;
  if (!path || !host?.readStagedFile || typeof createImageBitmap !== "function") {
    return artifact;
  }
  try {
    const result = await host.readStagedFile({ path });
    if ("error" in result) {
      return artifact;
    }
    const bitmap = await createImageBitmap(new Blob([result.bytes], { type: "image/png" }));
    return {
      ...artifact,
      texture: { image: bitmap, width: bitmap.width, height: bitmap.height },
    };
  } catch {
    return artifact;
  }
}
