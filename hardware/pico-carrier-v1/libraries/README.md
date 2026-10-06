# Project library provenance

The symbols and footprints in this directory are from the KiCad community
libraries distributed with KiCad 10.0.6, read on 2026-10-06. The installed
Flatpak library extension was `org.kicad.kicad.Library`, commit
`5a7d69b241b1417e15f791cb32499119ec931accda6a18544b2f9969d60da867`.

Sources:

- [KiCad symbols](https://gitlab.com/kicad/libraries/kicad-symbols):
  `MCU_Module:RaspberryPi_Pico`, `Connector_Generic:Conn_01x19`,
  `Connector_Generic:Conn_01x10`, `Mechanical:MountingHole`.
- [KiCad footprints](https://gitlab.com/kicad/libraries/kicad-footprints):
  `Module:RaspberryPi_Pico_Common_THT`,
  `Connector_PinHeader_2.54mm:PinHeader_1x19_P2.54mm_Vertical`,
  `Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical`,
  `MountingHole:MountingHole_3.2mm_M3`.

Copyright belongs to the respective KiCad library contributors. These vendored
library files, including the modified Pico footprint, are distributed under
CC-BY-SA 4.0 with KiCad's design exception; see [LICENSE.md](LICENSE.md).

`Pico_Socketed_RP2040` retains the upstream pad geometry and USB clearance. It
removes the Pico W antenna rule area and its annotations because this prototype
targets the non-wireless RP2040 Pico. It enables the 8.5 mm socket 3D model and
raises the Pico H model by 8.5 mm. Unused grouping metadata was removed and the
name, value and description changed. Other footprints and the symbol bodies
are unchanged apart from serialization. Project instances set their own values
and footprint assignments.

3D STEP models are referenced through `KICAD10_3DMODEL_DIR` and are **not**
vendored. Install KiCad's standard 3D libraries for the interactive 3D view.
The schematic and PCB do not need those models for editing or manufacturing.
No Bread80 or rgbwalker PCB layout or artwork has been copied into this design.
