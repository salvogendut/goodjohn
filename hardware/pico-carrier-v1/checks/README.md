# Validation record

Checked on 2026-10-06 with KiCad 10.0.6. The carrier is an **unbuilt prototype**;
these are design/file checks, not recorded physical measurements.

| Check | Result |
| --- | --- |
| [Schematic ERC](erc.json) | 0 violations at enabled error/warning severities |
| [PCB DRC](drc.json) | 0 violations, 0 unconnected items, 0 schematic parity issues |
| [Independent pin-map check](pinmap.json) | 19 matrix nets / 57 signal pads match firmware and both wiring SVGs; seven GND pads and all isolated pins checked |
| [Fabrication check](fabrication.json) | 92 PTH + 4 NPTH drill positions/diameters match final PCB; outline 80 × 66 mm; 2 layers / 1.6 mm |
| Visual review | Schematic PDF, both assembly PDF pages, component-side SVG and complete 3D preview inspected |
| Regeneration | Separate ignored build directory: regenerated schematic/placement, imported saved SES, applied v1 routing adjustments, reran ERC/DRC/parity/pin-map checks; all passed |

Final board rules enforce 0.25 mm minimum trace width and copper clearance,
0.80 mm minimum via diameter, 0.20 mm minimum via annulus, 0.50 mm copper-to-edge
clearance and 0.15 mm silkscreen clearance. Actual tracks are 0.30 mm; vias are
0.80 / 0.40 mm. No DRC exclusions are recorded. Normal KiCad default ignored
ERC categories are listed in its report.

`carrier.dsn` and `carrier.ses` preserve the local Freerouting input/result.
The final PCB also contains the uniform-width and ground-stitch adjustments
performed by `hardware/tools/route.py`; the SES alone is not the final PCB.
See [the tooling guide](../../tools/README.md) before regenerating anything.

Manufacturing artifacts and design files are covered by the
[SHA256 manifest](../fabrication/SHA256SUMS.txt). Revalidate and regenerate
exports after changing the schematic, PCB or manufacturing rules.
