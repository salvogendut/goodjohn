# Prototype fabrication files

`goodjohn-carrier-v1-gerbers.zip` contains the seven Gerber layers, two Excellon
drill files and the Gerber job file in [gerbers/](gerbers). These were exported
from the routed, zone-filled KiCad PCB after a clean DRC/parity check.

| Parameter | Value |
| --- | --- |
| Outline | 80 × 66 mm; single rectangular board |
| Stack | 2 copper layers; 1.6 mm FR4; 35 µm / 1 oz copper |
| Tracks | 0.30 mm; project minimum 0.25 mm |
| Copper clearance | Project minimum 0.25 mm; routing target 0.30 mm |
| Copper to board edge | Minimum 0.50 mm |
| Vias | 13 × 0.80 mm diameter / 0.40 mm finished drill; tent both sides |
| Component plated holes | 79 × 1.00 mm |
| Mounting holes | 4 × 3.20 mm **non-plated** |
| Solder mask / legend | Both sides; green mask / white legend suggested |
| Finish | Lead-free HASL or ENIG; no controlled impedance requirement |
| Assembly | Hand soldering; no stencil or pick-and-place file needed |

All Gerber and drill files use the same absolute origin, metric units and no
mirroring. The board starts at KiCad coordinates (100,100) mm; do not realign
individual layers. `Edge_Cuts.gm1` is the single routed outline. There are no
slots, milling cutouts or inner copper layers. Do not add copper plating to
the four mounting holes.

Outline dimensions refer to the centreline of its 0.05 mm drawing stroke.
KiCad's Gerber job bounding box includes that stroke and reports 80.05 × 66.05 mm;
the four outline corner coordinates define the intended **80 × 66 mm** board.
The [export check](../checks/fabrication.json) compares all 92 plated and four
unplated drill locations/diameters to the final PCB and checks the profile corners.

| Extension | Layer |
| --- | --- |
| `.gtl`, `.gbl` | Front / back copper |
| `.gts`, `.gbs` | Front / back solder mask openings |
| `.gto`, `.gbo` | Front / back silkscreen |
| `.gm1` | Board outline |
| `-PTH.drl` | Plated component holes and vias |
| `-NPTH.drl` | Four unplated mounting holes |

Check the manufacturer's layer preview, dimensions and NPTH interpretation
before ordering. This is an **unbuilt prototype**; first-board assembly and
bench testing remain pending. No fabrication order has been placed.

[SHA256SUMS.txt](SHA256SUMS.txt) records the design, reports and individual
fabrication files used for this export. Check from the carrier directory with
`sha256sum -c fabrication/SHA256SUMS.txt`.
