# /team:scientific-check

Gate any scientific or metric claim. Respect `AGENTS.md`.

1. Ask: does this change claim absolute elevation, accuracy, or a
   benchmark result? If no, say so and stop.
2. If yes, require: calibration/reference method, units, dataset
   manifest, checkpoint hash + upstream revision, and the numbers
   (RMSE/MAE/correlation/stability, with significance where claimed).
3. Verify relative-vs-metric semantics: uncalibrated output must be
   `metric=false`, units absent, LOCAL frame.
4. Confirm the claim's home: research issues stay research until
   promoted via `docs/project/RESEARCH_VS_PRODUCT.md`.
5. Refuse to mark Done when evidence is missing — record exactly what
   is missing instead.
