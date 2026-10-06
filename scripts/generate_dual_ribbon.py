#!/usr/bin/env python3
"""Generate the Bread80 CPC464 SMT J1 two-ribbon wiring documents.

J1 nets and link-pad numbers were inspected at BREAD_REV. GPIO assignments
come from the same firmware-derived dataset as the original 19-pin sheet.
"""

from copy import deepcopy
import xml.etree.ElementTree as ET

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Preformatted, Table, TableStyle, PageBreak, Spacer,
)

from generate_pinout import ROOT, BY_NET, BREAD_REV, BREAD_SOURCE

REVISION = "Revision 1 / 2026-10-06"
STEM = "wiring-dual-ribbon"
SCHEMATIC_SOURCE = f"https://github.com/Bread80/CPC_Keyboards/blob/{BREAD_REV}/Keyswitch_CPC464_SMT/Keyboard.kicad_sch"
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)

# Each list is one physical column of J1, counted from the square-pad end.
# LK1 1-2 connects J1.2 to X8; LK2 1-2 connects J1.1 to Y10; LK3 is open.
RIBBON_NETS = {
    "A": ["Y10", "X1", "X2", "X3", "X4", "X5", "X6", "X7", "X9", None],
    "B": ["X8", "Y9", "Y8", "Y7", "Y6", "Y5", "Y4", "Y3", "Y2", "Y1"],
}
CONTACTS = []
for ribbon, nets in RIBBON_NETS.items():
    for pos, net in enumerate(nets, 1):
        CONTACTS.append(dict(
            ribbon=ribbon, pos=pos, pad=2 * pos - 1 if ribbon == "A" else 2 * pos, net=net,
            gpio=BY_NET[net]["gpio"] if net else None,
            pin=BY_NET[net]["pin"] if net else None,
        ))
WIRES = [w for w in CONTACTS if w["net"]]
assert {w["net"] for w in WIRES} == set(BY_NET) and len(WIRES) == 19
BY_DUAL_NET = {w["net"]: w for w in WIRES}

ORIENTATION = """       KEYBOARD COMPONENT SIDE / KEYS FACING YOU
                    Rear / Esc end

           Ribbon B             Ribbon A
              B1 ( 2)          [ 1] A1  square pad
              B2 ( 4)          ( 3) A2
              B3 ( 6)          ( 5) A3
              B4 ( 8)          ( 7) A4
              B5 (10)          ( 9) A5
              B6 (12)          (11) A6
              B7 (14)          (13) A7
              B8 (16)          (15) A8
              B9 (18)          (17) A9
             B10 (20)          (19) A10 -- no connection

                    Space-bar end
       Parenthesized numbers are Bread80 J1 PCB pad numbers.
"""
CHECKS = [
    ("Top-row 1", "X1", "Y9"), ("Top-row 2", "X2", "Y9"),
    ("Esc", "X3", "Y9"), ("Space", "X8", "Y6"),
    ("Either Shift", "X6", "Y3"), ("DEL (Backspace)", "X9", "Y10"),
    ("Main Enter", "X3", "Y3"), ("Cursor Up", "X1", "Y1"),
]


def wire_rows():
    return [[f"{w['ribbon']}{w['pos']}", str(w["pad"]), w["net"] or "NC",
             f"GP{w['gpio']}" if w["net"] else "--",
             str(w["pin"]) if w["net"] else "Leave disconnected"] for w in CONTACTS]


def check_rows():
    rows = []
    for key, xnet, ynet in CHECKS:
        x, y = BY_DUAL_NET[xnet], BY_DUAL_NET[ynet]
        rows.append([key, f"{x['ribbon']}{x['pos']} / {y['ribbon']}{y['pos']}",
                     f"{x['pad']} / {y['pad']}", f"{x['pin']} / {y['pin']}"])
    return rows


def markdown_table(headers, rows):
    return "\n".join("| " + " | ".join(r) + " |" for r in
                     [headers, ["---"] * len(headers), *rows])


def generate_text():
    table = markdown_table(["Ribbon position", "J1 PCB pad", "Net", "Pico GPIO", "Pico physical pin"], wire_rows())
    checks = markdown_table(["Key held", "Ribbon pair (X / Y)", "J1 pads", "Pico physical pins"], check_rows())
    md = f"""# Bread80 CPC464 SMT: two 10-pin ribbons to Pico

{REVISION}. **Source-checked; this J1 harness has not been bench-tested.**
The rgbwalker J3-style harness has its own [hardware test record](wiring.md#hardware-test-record-2026-10-06).

[![Two-ribbon J1 wiring to Raspberry Pi Pico]({STEM}.svg)]({STEM}.svg)

Companions: [ASCII pinout](pinout-dual-ribbon.txt) and [two-page PDF](pinout-dual-ribbon.pdf).

## Exact target and link settings

This scheme is for **Bread80 `Keyswitch_CPC464_SMT`, keyboard connector J1
(Membrane 464/6128), configured for CPC464**, at revision `{BREAD_REV}`.
J1 has two columns of ten contacts for two 10-way ribbons. These are nineteen
matrix signals plus one unused contact; no matrix power or ground wire is needed.
The Pico is an original RP2040 Pico / Pico H, powered by its USB data connection
to the PC. Disconnect the keyboard from the CPC motherboard entirely.

With USB unplugged, configure the **keyboard PCB** links:

| Link | Required state | Electrical effect |
| --- | --- | --- |
| LK1 | Bridge pads **1-2** only (CPC464 end); pad 3 remains open | J1 pad 2 / B1 connects to X8 |
| LK2 | Bridge pads **1-2** | J1 pad 1 / A1 connects to Y10 |
| LK3 | **Open** | X8 and X9 remain separate |
| LK4, LK5, LK6 | **Open** for initial testing | Bonus switches remain disconnected |

LK1 pad 1 is the square pad on that link. Use pad numbers and verify with a
meter; upstream text/silkscreen contains inconsistent JP/LK references. The
net connections above were checked in the PCB and schematic.

The existing firmware GPIO assignments and keymap apply to this harness.
The conservative diode option OFF can be kept for initial testing. If every
switch diode is fitted and its orientation verified, setting
`GOODJOHN_MATRIX_HAS_DIODES=ON` permits chords that the default ghost filter
would otherwise suppress. No connector-specific firmware remapping is needed.

This table does not cover the CPC6128 link setting, Bread80's J2 modular
connector, the Tactile board's J2/J3, or an original membrane tail whose contact
order has not been verified. On this sheet **J1 means the keyboard connector**;
the J1 in the original [19-pin SVG](wiring.svg) names a proposed adapter instead.

## Connector orientation and numbering

```text
{ORIENTATION.rstrip()}
```

**A and B are labels defined by this guide**, not additional PCB references.
Count A1 and B1 from the same end, next to square J1 pad 1. Ribbon A uses the
**odd** J1 pads; ribbon B uses the **even** pads. A10 is J1 pad **19** and stays
disconnected. B10 is J1 pad **20** and is required for Y1.

Bread80's schematic labels the A ends as original CPC pins 1/10 and the B ends
as 11/20. Those are not the KiCad J1 pad numbers. This guide always distinguishes
ribbon position, J1 PCB pad number, GPIO number and Pico physical pin number.
The solder-side view is mirrored; identify square pad 1 on the actual board.
Check cable continuity even when both ends use identical housings or colors.

## Complete wiring scheme

{table}

Only GP2 through GP20 are used. All other Pico header pins stay unconnected
to the keyboard. On a Pico viewed component-side up with USB at the top, physical
pins 1-20 run down the left, and 21-40 run up the right.

## Continuity and staged power-up

1. Disconnect USB and the CPC motherboard. Fit the links above.
2. Verify J1.1 to Y10 (also J3.2), and J1.2 to X8 (also J3.10), each near zero
   ohms without a key held. Verify X8 (J3.10) and X9 (J3.1) are not shorted.
3. Connect A2 / J1.3 to Pico physical 16, and B2 / J1.4 to physical 14. Check
   both individual wires pad-to-pad without holding a key, then connect USB.
   Press top-row `1`; it should type `1`.
4. Unplug USB, add A3 / J1.5 to physical 17, then test `2`. Next add A4 / J1.7
   to physical 19 for Esc. Esc does not print a character.
5. Complete the remaining connections, checking each wire before power-up.
   Test digits, letters, modifiers, both Enter keys, cursor/keypad keys and DEL.
   Test Space and DEL separately to check X8 and the isolated X9/Y10 path.

For switch-pair checks, disconnect the keyboard from the Pico as well. On the
diode board, use diode mode: red probe on X and black probe on Y. Pressed should
conduct in that direction; released should be open. A continuity beeper may not
detect a diode reliably. The Pico pin column below identifies the harness
endpoints; perform these switch-identification measurements on the detached keyboard.

{checks}

## Sources and regeneration

- [Bread80 PCB at the inspected revision]({BREAD_SOURCE}): J1 pads, connector orientation and LK1-LK6 nets.
- [Matching schematic]({SCHEMATIC_SOURCE}): CPC464/CPC6128 routing, ribbon numbering and matrix switch paths.
- `src/board_config.h`: GPIO assignments, shared with the existing firmware.

Install `scripts/requirements-docs.txt`, then run:

```sh
python3 scripts/generate_dual_ribbon.py
```

The generator creates this Markdown scheme, the ASCII/PDF sheets and the SVG
from one connector dataset. Pico vector artwork comes from `pico-pinout.svg`.
"""
    (ROOT / "docs" / f"{STEM}.md").write_text(md)
    lines = ["GOODJOHN - BREAD80 CPC464 SMT J1 / TWO 10-PIN RIBBONS", REVISION,
             "SOURCE-CHECKED; NOT BENCH-TESTED. CPC464 CONFIGURATION ONLY.", "",
             "USB unplugged for wiring. Keyboard disconnected from CPC motherboard.",
             "LK1: bridge 1-2 only. LK2: bridge 1-2. LK3 and LK4-LK6: OPEN.",
             "19 signal wires; no keyboard power or ground wire. Pico USB goes to PC.", "",
             ORIENTATION, "A/B are guide labels. A = odd J1 pads; B = even J1 pads.",
             "J1 pad 19 (A10) is unused. J1 pad 20 (B10) MUST be wired.", "",
             "Ribbon   J1 pad   Net    Pico GPIO   Pico PHYSICAL pin", "-" * 72]
    lines.extend(f"{r[0]:<9}{r[1]:<9}{r[2]:<7}{r[3]:<12}{r[4]}" for r in wire_rows())
    lines += ["", "Link checks, no keys held: J1.1 -> J3.2 (Y10); J1.2 -> J3.10 (X8).",
              "Both must conduct. LK3 must not short J3.10 (X8) to J3.1 (X9).", "",
              "Start with A2/J1.3 -> Pico16 and B2/J1.4 -> Pico14; top-row 1 types 1.",
              "Unplug USB between changes. Add A3/J1.5 -> Pico17 for 2;",
              "A4/J1.7 -> Pico19 for Esc; then complete the harness above.",
              "Existing firmware GPIO/keymap applies. Diode option ON only after",
              "all switch diodes and their orientation have been verified.", "",
              "SWITCH CHECKS: detach keyboard from Pico; red on X, black on Y.",
              "Use diode mode on the SMT board. Pressed: conducts; released: open.",
              "Key                Ribbon X/Y   J1 pads X/Y   Pico physical X/Y"]
    lines.extend(f"{r[0]:<19}{r[1]:<13}{r[2]:<14}{r[3]}" for r in check_rows())
    lines += ["", "Do not apply to CPC6128 settings, J2 modular, Tactile J2/J3, or an",
              "unverified original membrane tail. The original 19-pin SVG's adapter",
              "J1 and this KEYBOARD J1 are different connector references.", "",
              "PCB source:", BREAD_SOURCE, "Schematic:", SCHEMATIC_SOURCE,
              "Full notes: docs/wiring-dual-ribbon.md",
              "Regenerate: python3 scripts/generate_dual_ribbon.py", ""]
    text = "\n".join(lines)
    assert text.isascii()
    (ROOT / "docs/pinout-dual-ribbon.txt").write_text(text, encoding="ascii")


def generate_svg():
    bg, muted = "#f8fafb", "#526572"
    svg = ET.Element(f"{{{SVG}}}svg", dict(viewBox="0 0 1600 1420", width="1600", height="1420",
                                         role="img", **{"aria-labelledby": "title description"}))

    def node(tag, attrs=None, text=None, parent=svg):
        e = ET.SubElement(parent, f"{{{SVG}}}{tag}", {k.replace("_", "-"): str(v) for k, v in (attrs or {}).items()})
        e.text = text
        return e

    def label(x, y, text, size=17, fill="#243847", weight="400", anchor="start"):
        return node("text", dict(x=x, y=y, font_family="Arial, Helvetica, sans-serif", font_size=size,
                                 fill=fill, font_weight=weight, text_anchor=anchor), text)

    node("title", {"id": "title"}, "Goodjohn: Bread80 CPC464 SMT J1 two-ribbon wiring to Pico")
    node("desc", {"id": "description"},
         "Keyboard J1 configured for CPC464. Ribbon A uses odd PCB pads; B uses even pads. "
         "Bridge LK1 pads 1-2 and LK2; leave LK3 open. Nineteen wires preserve X8 and X9 separately. "
         "A10, J1 pad 19, is unused. B10, J1 pad 20, connects Y1. USB supplies power and data. "
         "Source-checked wiring guide, not bench-tested or a PCB layout.")
    node("rect", dict(width=1600, height=1420, fill="white"))
    source = ET.parse(ROOT / "pico-pinout.svg").getroot()
    svg.append(deepcopy(source.find(f"{{{SVG}}}style")))
    artwork = next(n for n in source.iter() if n.get("id", "").startswith("Picoboard_Icon_") and len(n))
    label(48, 46, "GOODJOHN / ALTERNATE CONNECTOR", 16, "#076879", "700")
    label(48, 91, "Two 10-pin ribbons to Raspberry Pi Pico", 32, weight="700")
    label(48, 124, "Bread80 CPC464 SMT keyboard J1 / CPC464 link setting / 19 matrix signals", 19, muted)
    node("rect", dict(x=40, y=150, width=1520, height=72, rx=10, fill="#fff3db"))
    label(60, 179, "KEYBOARD LINKS: LK1 bridge pads 1-2 only; LK2 bridge pads 1-2; LK3 OPEN.", 20, weight="700")
    label(60, 205, "Leave LK4-LK6 open. Disconnect CPC motherboard. Unplug USB before changing wires or links.", 17)
    node("rect", dict(x=40, y=245, width=1520, height=1080, rx=18, fill=bg, stroke="#cdd9df"))
    label(1515, 275, "Wiring guide: ribbons drawn separately; see orientation inset below", 15, muted, anchor="end")

    scale, pitch = 1.50, 18.7102204 * 1.50
    left_x, first_y = 1000., 415.
    dx, dy = left_x - scale * 270.5741577, first_y - scale * 121.6880493
    right_x = dx + scale * 401.5894775
    center_x = (left_x + right_x) / 2
    board = node("g", {"id": "pico-artwork", "transform": f"translate({dx} {dy}) scale({scale})"})
    board.append(deepcopy(artwork))

    def pico_pin(pin):
        return (left_x, first_y + (pin - 1) * pitch) if pin <= 20 else (right_x, first_y + (40 - pin) * pitch)

    node("path", dict(d=f"M {center_x} 380 V 325 H 1330", fill="none", stroke=muted, stroke_width=3))
    node("rect", dict(x=1330, y=301, width=183, height=48, rx=7, fill="#e5edf1"))
    label(1421, 332, "PC USB port", 20, weight="700", anchor="middle")
    label(1290, 297, "power + keyboard data", 15, muted)
    label(center_x, 986, "Raspberry Pi Pico / Pico H", 20, weight="700", anchor="middle")
    label(center_x, 1009, "Component side / USB at top", 15, muted, anchor="middle")

    for ribbon, top in (("A", 285), ("B", 705)):
        node("rect", dict(x=65, y=top, width=365, height=398, rx=10, fill="white", stroke="#b7c8d1"))
        label(82, top + 30, f"RIBBON {ribbon} / 1 x 10", 23, weight="700")
        parity = "odd" if ribbon == "A" else "even"
        label(82, top + 55, f"Keyboard J1 {parity} pads", 17, muted)
        for x, name in ((85, "pos."), (153, "J1 pad"), (221, "net"), (286, "GPIO / pin")):
            label(x, top + 83, name, 15, muted)

    def contact_y(w):
        return (390 if w["ribbon"] == "A" else 810) + (w["pos"] - 1) * 28

    paths = node("g", {"id": "signal-wires", "fill": "none", "stroke-linejoin": "round"})
    for w in WIRES:
        cy, gpio, pin = contact_y(w), w["gpio"], w["pin"]
        sx, sy = pico_pin(pin)
        color = "#087787" if w["net"].startswith("Y") else "#7551ad"
        if pin > 20:
            idx = gpio - 16
            inner, outer, below = 462 + 27 * idx, 1350 + 34 * idx, 1150 + 27 * idx
            d = f"M 425 {cy} H {inner} V {below} H {outer} V {sy} H {sx}"
        elif w["net"].startswith("X"):
            track = 635 + (gpio - 12) * 60
            d = f"M 425 {cy} H {track} V {sy} H {sx}"
        else:
            d = f"M 425 {cy} H 600 C 740 {cy}, 760 {sy}, 870 {sy} H {sx}"
        g = node("g", {"id": f"wire-{w['ribbon']}{w['pos']}", "data-ribbon": w["ribbon"],
                       "data-position": w["pos"], "data-j1-pad": w["pad"], "data-net": w["net"],
                       "data-gpio": gpio, "data-pico-pin": pin}, parent=paths)
        node("title", text=f"{w['ribbon']}{w['pos']} / J1 pad {w['pad']}: {w['net']} to GP{gpio}, Pico physical {pin}", parent=g)
        node("path", dict(d=d, stroke=bg, stroke_width=7), parent=g)
        node("path", dict(d=d, stroke=color, stroke_width=2.5), parent=g)

    for w in CONTACTS:
        cy, net = contact_y(w), w["net"]
        color = ("#087787" if net.startswith("Y") else "#7551ad") if net else muted
        node("rect", dict(x=77, y=cy-12, width=327, height=24, rx=4, fill="#edf5f6" if net and net.startswith("Y") else "#f3eff8"))
        label(85, cy+6, f"{w['ribbon']}{w['pos']}", 16, color, "700")
        label(153, cy+6, f"{w['pad']:02}", 16, color)
        label(221, cy+6, net or "NC", 16, color)
        label(286, cy+6, f"GP{w['gpio']} / {w['pin']:02}" if net else "no wire", 16, color)
        if w["pad"] == 1:
            node("rect", dict(x=419, y=cy-6, width=12, height=12, fill=color, stroke="white"))
        elif net:
            node("circle", dict(cx=425, cy=cy, r=5, fill=color, stroke="white"))
        else:
            node("path", dict(d=f"M 419 {cy-6} l 12 12 M 419 {cy+6} l 12 -12", stroke=color, stroke_width=2))
        if net:
            sx, sy = pico_pin(w["pin"])
            node("circle", dict(cx=sx, cy=sy, r=3.5, fill=color, stroke="white"))
            lx = sx - 125 if w["pin"] <= 20 else sx + 12
            node("rect", dict(x=lx-4, y=sy-13, width=112, height=24, rx=3, fill=bg))
            label(lx, sy+5, f"GP{w['gpio']} / {w['pin']:02}", 16, color, "700")

    # A physical orientation inset, separate from the schematic wire routing.
    node("rect", dict(x=75, y=1130, width=330, height=180, rx=8, fill="white", stroke="#b7c8d1"))
    label(88, 1152, "J1: keyboard component-side view", 15, weight="700")
    label(88, 1173, "Rear / Esc end", 13, muted)
    label(210, 1173, "B", 15, weight="700", anchor="middle")
    label(249, 1173, "A", 15, weight="700", anchor="middle")
    for i in range(10):
        yy = 1191 + i * 10
        label(186, yy+3, str(2*i+2), 11, muted, anchor="end")
        label(278, yy+3, str(2*i+1), 11, muted)
        node("circle", dict(cx=210, cy=yy, r=2.7, fill="#087787"))
        if i == 0:
            node("rect", dict(x=246, y=yy-3, width=6, height=6, fill="#7551ad"))
            label(305, yy+3, "square 1", 10, muted)
        else:
            node("circle", dict(cx=249, cy=yy, r=2.7, fill="#7551ad" if i != 9 else muted))
    label(88, 1301, "Space-bar end / numbers = PCB pads", 13, muted)
    label(647, 1058, "A10 = J1 pad 19: leave disconnected", 17, weight="700")
    label(647, 1085, "B10 = J1 pad 20: REQUIRED (Y1)", 17, weight="700")
    label(647, 1112, "A/B are labels for this guide. Follow pad numbers.", 15, muted)
    label(49, 1353, "Nineteen signal wires only. No keyboard power or ground wire. Crossings are not electrical junctions.", 17, weight="700")
    label(49, 1380, "Source-checked; not bench-tested. Target: Bread80 CPC464 SMT J1, CPC464 setting. Details: docs/wiring-dual-ribbon.md", 15, muted)
    label(49, 1404, "Pico vector artwork adapted from supplied pico-pinout.svg. Not a PCB layout. Other connector versions need separate mapping.", 13, muted)
    ET.indent(svg, space="  ")
    ET.ElementTree(svg).write(ROOT / "docs" / f"{STEM}.svg", encoding="utf-8", xml_declaration=True)


def generate_pdf():
    ink, teal = colors.HexColor("#243847"), colors.HexColor("#076879")
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13, textColor=ink, spaceAfter=8)
    title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=21, leading=26, spaceAfter=12)
    heading = ParagraphStyle("heading", parent=body, fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=teal)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=11)
    mono = ParagraphStyle("mono", fontName="Courier", fontSize=8, leading=10)
    story = []

    def p(text, style=body):
        story.append(Paragraph(text, style))

    def table(headers, rows, widths, height=20):
        t = Table([headers, *rows], colWidths=widths, rowHeights=height)
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), ink), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f6")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([t, Spacer(1, 12)])

    p("Two 10-pin ribbons to Pico", title)
    p("<b>Bread80 CPC464 SMT / keyboard J1 / CPC464 link setting.</b><br/>Original RP2040 Pico or Pico H. Source-checked; this harness has not been bench-tested.")
    p("<b>Unplug USB before wiring.</b> Disconnect the CPC motherboard. Bridge <b>LK1 pads 1-2 only</b> and <b>LK2 pads 1-2</b>. Leave <b>LK3 and LK4-LK6 open</b>.")
    p("Ribbon A = odd J1 pads; ribbon B = even J1 pads. A/B are guide labels. Count both ribbons from the square J1 pad 1 end. Nineteen signals; no matrix power or ground wire.")
    table(["Ribbon pos.", "J1 PCB pad", "Net", "Pico GPIO", "Pico PHYSICAL pin"], wire_rows(), [86, 87, 60, 102, 184])
    p("<b>A10 / J1 pad 19 is unused. B10 / J1 pad 20 must connect to Y1.</b> GPIO numbers differ from physical pins. On the Pico component side, USB at top: physical 1-20 run down the left, 21-40 up the right.")
    p("The existing firmware GPIO assignments and keymap apply. Keep diode option OFF for initial testing; ON can be used once all switch diodes are fitted and verified.")
    p("Scope: this is the keyboard's J1, not the adapter J1 in the original 19-pin drawing. CPC6128 settings, J2 modular, Tactile J2/J3 and unverified original membrane tails need separate mappings.", small)
    story.append(PageBreak())
    p("Orientation and electrical checks", title)
    story.append(Preformatted(ORIENTATION, mono))
    p("Solder-side view is mirrored. The schematic's original CPC labels 1-10 / 11-20 differ from its odd/even J1 pad numbers. Verify the square pad and every cable endpoint.", small)
    p("Link checks and first USB test", heading)
    p("With USB unplugged, J1.1 to J3.2 (Y10) and J1.2 to J3.10 (X8) must each conduct without a key pressed. X8 (J3.10) and X9 (J3.1) must remain separate. LK1 pad 1 is square; its third pad remains open.")
    p("Start with <b>A2 / J1.3 to Pico physical 16</b> and <b>B2 / J1.4 to physical 14</b>. Check each wire, connect USB, then test top-row 1. Unplug USB between changes: add A3 / J1.5 to physical 17 for 2, and A4 / J1.7 to physical 19 for Esc. Complete the harness and test each key.")
    p("Switch checks: keyboard disconnected from both Pico and CPC. Use diode mode, <b>red on X, black on Y</b>. Pressed conducts; released is open. The Pico column identifies the eventual harness endpoints.", small)
    table(["Key held", "Ribbon X / Y", "J1 pads X / Y", "Pico physical X / Y"], check_rows(), [137, 120, 112, 150], 19)
    p(f'<b>Sources:</b> <link href="{BREAD_SOURCE}" color="#076879">Bread80 PCB</link> and <link href="{SCHEMATIC_SOURCE}" color="#076879">schematic</link>, revision {BREAD_REV}. GPIO assignments: src/board_config.h.', small)
    p("Full notes: docs/wiring-dual-ribbon.md. Vector diagram: docs/wiring-dual-ribbon.svg. Regenerate all companions with python3 scripts/generate_dual_ribbon.py.", small)

    def footer(c, doc):
        c.setStrokeColor(colors.HexColor("#c6d2d9"))
        c.line(38, 37, A4[0]-38, 37)
        c.setFont("Helvetica", 8)
        c.setFillColor(ink)
        c.drawString(38, 24, REVISION + " | Bread80 J1 CPC464 | Not bench-tested")
        c.drawRightString(A4[0]-38, 24, str(doc.page))

    doc = SimpleDocTemplate(str(ROOT / "docs/pinout-dual-ribbon.pdf"), pagesize=A4,
                            rightMargin=38, leftMargin=38, topMargin=38, bottomMargin=48,
                            title="Goodjohn - Bread80 J1 two-ribbon Pico pinout", author="Goodjohn project",
                            invariant=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    generate_text()
    generate_svg()
    generate_pdf()
    print("Generated dual-ribbon SVG, Markdown scheme, ASCII and PDF pinouts.")
