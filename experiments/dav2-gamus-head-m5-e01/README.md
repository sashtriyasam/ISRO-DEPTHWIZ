# dav2-gamus-head-m5-e01

Frozen DA-V2-Small + lightweight head on GAMUS (research).
- Train (24): `DC_01_25`, `DC_02_24`, `DC_02_25`, `DC_02_27`, `DC_03_23`, `DC_03_24`, `DC_03_25`, `DC_03_27`, `DC_03_28`, `DC_04_24`, `DC_04_25`, `DC_04_26`, `DC_04_28`, `DC_05_20`, `DC_05_21`, `DC_05_26`, `DC_05_27`, `DC_05_29`, `DC_06_20`, `DC_06_21`, `DC_06_26`, `DC_06_27`, `DC_06_28`, `DC_06_29`
- Val (8): `DC_02_26`, `DC_04_23`, `DC_04_27`, `DC_08_31`, `DC_09_33`, `DC_10_30`, `DC_11_16`, `DC_11_33`
- Best val MAE: 5.1500 m @ epoch 23 (selection on VAL only; test unused).
- Output: metric GAMUS nDSM/AGL prediction (research evaluation only; not calibrated elevation).

See `config.json`, `results.json`, `log.jsonl`, `checkpoints/best.pt` (git-ignored).
