# Prototype wiring

This is a wiring proposal checked against source files, **not a bench-validated
schematic or an interface PCB ready for manufacture**. GPIO numbers below are
for the original non-wireless RP2040 Raspberry Pi Pico. On 2026-10-06, the user
confirmed digits, all letter rows, Esc and main Enter on rgbwalker V1.2 with a
completed 19-wire direct harness. Further key/chord and USB tests remain pending.

Printable companions: [ASCII pinout](pinout.txt) and [detailed PDF](pinout.pdf).
The [SVG wiring overview](wiring.svg) shows the Pico and a proposed J1 adapter
connector with the same contact numbering as the keyboard's J3. It is a wiring
guide, not a PCB layout; J1 contact 1 is drawn at the bottom and crossings are
not electrical junctions.
The PDF includes all 40 Pico header positions, the 19-wire J3 harness and
unpowered switch checks. It distinguishes the source-checked J3 mapping from
the rgbwalker V1.2 connector checks and initial hardware test.

The keyboard must be disconnected electrically from the CPC motherboard,
including when that motherboard is powered off. This firmware drives the matrix
and is not a passive sniffer. The Pico GPIO interface is 3.3 V; do not connect
CPC 5 V logic or USB VBUS to a matrix pin. The passive switch matrix does not
need a VCC supply. Power the Pico through its USB connector.

## Physical matrix

The firmware follows Bread80's net names: rows `Y1..Y10` and columns `X1..X9`.
Indices in the C arrays are zero based. Most keys occupy Y1..Y9 by X1..X8;
DEL occupies Y10/X9. The familiar CPC logical 10-by-8 scan hides the separate
DEL sense wire by joining X8 and X9 on the computer side. The standalone Pico
prototype preserves both wires, using 19 GPIOs.

Both Shift switches occupy Y3/X6. Software cannot tell them apart. The optional
Bread80 bonus keys can be connected to Y10/X5 and Y10/X6 by its links, but those
positions are currently unmapped in the firmware.

For the diode board, the PCB connects diode pad 1 (cathode) to Y and the switch
side to X through pad 2 (anode). The scan therefore pulls one Y low and reads
X inputs with 3.3 V pull-ups. All other Y pins remain high impedance. This also
avoids opposing GPIO outputs through simultaneous presses on boards without
diodes. No matrix output is driven high.

## Bread80 CPC464 SMT: J3 inline connector

This table comes from pad nets in
`../CPC_Keyboards/Keyswitch_CPC464_SMT/Keyboard.kicad_pcb` at revision
`bf4a6052888fef27ca01a6b0983791d7cb4e8af1`.
J3 is a **19-pin** footprint in this source revision. Numbers refer to KiCad
pad numbers, not left-to-right appearance in a photograph. Locate pad 1 on the
actual board and verify continuity before connecting the Pico.

| Matrix net | J3 pad | Pico GPIO | Pico physical header pin |
| --- | ---: | ---: | ---: |
| Y1 | 19 | 2 | 4 |
| Y2 | 18 | 3 | 5 |
| Y3 | 17 | 4 | 6 |
| Y4 | 16 | 5 | 7 |
| Y5 | 15 | 6 | 9 |
| Y6 | 14 | 7 | 10 |
| Y7 | 13 | 8 | 11 |
| Y8 | 12 | 9 | 12 |
| Y9 | 11 | 10 | 14 |
| Y10 | 2 | 11 | 15 |
| X1 | 3 | 12 | 16 |
| X2 | 4 | 13 | 17 |
| X3 | 5 | 14 | 19 |
| X4 | 6 | 15 | 20 |
| X5 | 7 | 16 | 21 |
| X6 | 8 | 17 | 22 |
| X7 | 9 | 18 | 24 |
| X8 | 10 | 19 | 25 |
| X9 (DEL only) | 1 | 20 | 26 |

For this J3 prototype keep LK1, LK2 and LK3 open so X8 and X9 remain separate.
These links are for adapting other connectors to the CPC motherboard, which is
absent here. In particular LK3 shorts X8/X9. Leave bonus-switch links open for
the first bring-up. There is no matrix ground or power pin in this J3 table.

The source PCB gives J1 (membrane) and J2 (modular) different pin orders from
J3, and their routing depends on the links. Do not apply this J3 table to them.
Their adapter profiles have not yet been implemented.

## rgbwalker Cherry keyboard

Reference checkout:
`../Amstrad_CPC_464_new_Cherry_Keyboard`, revision
`588e61006bb606d08cc981467d7990c6e3104c42`.
Its README describes a 20-pin inline connector and a diode-less switch BOM.
The included `_IMAGENES_/Matriz_Teclado.jpg` is a service-manual matrix drawing,
not a netlist for every released PCB revision.

That drawing puts DEL between connector positions 1 and 2, the eight ordinary
sense lines at positions 3..10, and the nine ordinary scan lines at 11..19.
Its labels for the two DEL wires are reversed relative to Bread80's PCB net
names. With an isolated switch and no diode that reversal does not affect DEL,
but it demonstrates why these names must not be treated as a universal pinout.

For **V1.2**, the inspected fabrication archive is
`_GERBER_V1.2_/Gerber_Amstrad_Teclado_09_PCB_Amstrad_Teclado_10_THT_Con_03_2025-03-02.zip`
at the revision above. Tracing its top/bottom copper and plated holes establishes:

- CP002_THT and CP002_SMD contacts 1 through 19 connect to the same respective
  nets. Contact 20 on each footprint is isolated from the switch matrix.
- With the keys facing you, count from the **square pad at the Esc end as 1**,
  toward Shift. Count contacts 1 and 2 even though they serve only DEL.
- Esc closes contacts **5/11**, top-row `1` closes **3/11**, top-row `2` closes
  **4/11**, and DEL closes **1/2**. The first three pairs also match the firmware
  mapping derived from Bread80 J3.

Use the contact numbers in the 19-wire table for this V1.2 prototype, leaving
contact 20 disconnected. The adapter J1 shown in the SVG is drawn with contact 1
at the bottom; that is not the orientation of the keyboard header. Verify the
actual pads and cable endpoints, rather than inferring them from cable colors.
Other PCB revisions still need their own connector checks.

### Staged bring-up for rgbwalker V1.2

Unplug USB before each wiring change or meter check. Keep the keyboard isolated
from the CPC motherboard. Use direct individual jumpers for these initial tests.

1. **Start with two wires:** keyboard contact 3 to Pico physical pin 16 (GP12),
   and keyboard contact 11 to Pico physical pin 14 (GP10). With no key pressed,
   check each wire from the keyboard solder pad to its intended Pico solder pad:
   each should read close to zero ohms / beep continuously. Connect USB and press
   top-row `1`; it should type `1`. This step passed on the user's V1.2 hardware.
2. **Add `2`:** keyboard contact 4 to Pico physical pin 17 (GP13). Check the new
   wire with USB unplugged, then reconnect USB. Top-row `1` and `2` should each
   type their own digit.
3. **Add Esc:** keyboard contact 5 to Pico physical pin 19 (GP14). After checking
   its wire, verify Esc in a keyboard event viewer or an application with a known
   Esc action. Esc does not print a character.
4. **Complete the number row:** add keyboard contacts 12, 13, 14, 15 and 16 to
   Pico physical pins 12, 11, 10, 9 and 7 respectively. Check each wire, then
   power up and type `1234567890` using the top-row keys.
5. **Complete the harness:** add the remaining connections from the wire list,
   checking each pad-to-pad connection before powering up. Test every key
   individually before modifiers and chords. Keep contact 20 disconnected.

### Hardware test record: 2026-10-06

The user completed the direct harness with the existing firmware and reported
that the following tests passed:

| Test | Confirmed result |
| --- | --- |
| Initial two-wire test | Top-row `1` types `1` |
| Add contact 4 | Top-row `1` and `2` type correctly |
| Add contact 5 | Esc works; `1` and `2` still type correctly |
| Add contacts 12 through 16 | Top-row digits produce `1234567890` |
| Complete all 19 wires | `qwertyuiop`, `asdfghjkl`, `zxcvbnm` and main Enter work |

This establishes basic typing on this V1.2 prototype. Individual results for
Space, Tab, modifiers/lock keys, DEL/CLR, punctuation, cursor and keypad keys
have not yet been recorded. Chords/ghost suppression, rollover, cable timing,
USB reconnect and suspend/resume/current also need hardware checks. Other board
variants retain their separate validation status.

The original ribbon/jumper assembly produced incorrect characters and failed
the intended end-to-end wire checks. Bypassing it with the two direct wires
restored `1`; completing the direct harness then passed the tests above. This
implicates the assembly or its connections, but does not establish which
connector, contact or wire was wrong. Do not shift the entire
harness or change the keymap on that evidence alone.

To reuse a ribbon or adapter, disconnect it from the Pico and map each keyboard
pad to its actual cable endpoint with the meter. Label those endpoints before
connecting them to the Pico. Each wire must conduct without any key held.
For a **switch** continuity test, disconnect the keyboard from the Pico entirely:
the expected pair should conduct only while that key is pressed. An unpowered
Pico can provide other meter paths through its circuitry, so its attached GPIOs
are not a reliable way to identify an unknown switch pair.

## Other CPC connectors

Bread80's tactile design has the same X/Y naming but different connector
references. CPC6128 and membrane adaptations can join X8/X9 and reroute Y10.
An 18-wire adapter needs either both sense GPIOs connected to the shared X8/X9
net or a scan normalization change for DEL. Do not simply omit X9 from the
current firmware: DEL will disappear. Diode and ghosting behavior must be
checked for the exact adaptation before claiming support.

The CPC6128 SMT board is identified by upstream as unfinished. No pin-for-pin
compatibility or physical fit is assumed for it.

## Continuity and first-power checks

With the keyboard disconnected from both Pico and CPC, test these representative
switch paths:

| Key | Expected matrix path | Bread80 J3 pads |
| --- | --- | --- |
| Top-row 1 | Y9 / X1 | 11 / 3 |
| Esc | Y9 / X3 | 11 / 5 |
| Cursor Up | Y1 / X1 | 19 / 3 |
| A | Y9 / X6 | 11 / 8 |
| Space | Y6 / X8 | 14 / 10 |
| Either Shift | Y3 / X6 | 17 / 8 |
| DEL | Y10 / X9 | 2 / 1 |
| Main Enter | Y3 / X3 | 17 / 5 |
| Keypad Enter | Y1 / X7 | 19 / 9 |

Use diode mode where necessary: current flows from X through the closed switch
and diode to Y. Confirm the other contacts remain open with keys released.

After wiring, first verify USB enumeration with no keys held. Check every key
individually, then Shift/Control/Alt chords and release behavior. On diode-less
boards, try three corners of a rectangle and confirm that no fourth phantom
key is reported; some real new presses will be suppressed. On diode boards,
verify those chords with `GOODJOHN_MATRIX_HAS_DIODES=ON`. Finish by checking
unplug/replug, host suspend/resume and Num Lock behavior. The current firmware
does not provide a USB-compliant low-power suspend implementation or remote wake.

## Source provenance

- [Bread80 CPC464 PCB at the inspected revision](https://github.com/Bread80/CPC_Keyboards/blob/bf4a6052888fef27ca01a6b0983791d7cb4e8af1/Keyswitch_CPC464_SMT/Keyboard.kicad_pcb): connector nets, diode orientation and switch coordinates.
- [Bread80 documentation at the inspected revision](https://github.com/Bread80/CPC_Keyboards/blob/bf4a6052888fef27ca01a6b0983791d7cb4e8af1/README.md): shared logical matrices and board maturity.
- [rgbwalker documentation at the inspected revision](https://github.com/rgbwalker/Amstrad_CPC_464_new_Cherry_Keyboard/blob/588e61006bb606d08cc981467d7990c6e3104c42/README.md): switch type, connector family and service-manual drawing.
- [rgbwalker V1.2 fabrication archive](https://github.com/rgbwalker/Amstrad_CPC_464_new_Cherry_Keyboard/blob/588e61006bb606d08cc981467d7990c6e3104c42/_GERBER_V1.2_/Gerber_Amstrad_Teclado_09_PCB_Amstrad_Teclado_10_THT_Con_03_2025-03-02.zip): THT/SMD contact correspondence, isolated contact 20 and the switch pairs recorded above.
- [Raspberry Pi Pico documentation](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html): Pico hardware and header pinout.
