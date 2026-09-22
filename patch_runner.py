import pathlib
path = pathlib.Path('src/depthwizard/pipeline/runner.py')
text = path.read_text()

# Add constant after _METRIC_TARGETS definition
text = text.replace('    }\n)\n\n', '    }\n)\n\nFLAT_DEPTH_STD_MEAN_THRESHOLD = 1e-6\n\n')

# Add method after _check_calibration
method = '''
    def _warn_if_flat_depth(self, depth: DepthResult) -> None:
        """Warn if depth output has near-zero variance (flat terrain)."""
        import math
        vals = depth.depth_values
        if not vals:
            return
        mean = math.fsum(vals) / len(vals)
        if mean == 0.0:
            return
        var = math.fsum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(var) if var > 0 else 0.0
        ratio = std / abs(mean) if mean != 0 else float('inf')
        if ratio < FLAT_DEPTH_STD_MEAN_THRESHOLD:
            self._warnings.append(f"Flat depth detected: output variance near zero (std/mean ratio = {ratio:.2e}). This may indicate a model failure on uniform imagery (e.g., map screenshots).")
'''

# Insert before _fail method
text = text.replace('    def _fail(', method + '    def _fail(')

# Call the method after self._depth = depth (after semantic preprocessor block)
text = text.replace('        self._depth = depth\n\n        if self._cancelled():', '        self._depth = depth\n        self._warn_if_flat_depth(self._depth)\n\n        if self._cancelled():')

path.write_text(text)
print('Updated runner.py')