#!/usr/bin/env python3
"""Draw the minimal adapter wiring using the supplied Pico vector artwork."""

from copy import deepcopy
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def generate(root_path, wires):
    if {w["gpio"] for w in wires} != set(range(2, 21)):
        raise ValueError("Update the SVG routing layout for GPIO assignments outside GP2-GP20")
    original = ET.parse(root_path / "pico-pinout.svg").getroot()
    artwork = next(n for n in original.iter()
                   if n.get("id", "").startswith("Picoboard_Icon_") and len(n))
    svg = ET.Element(f"{{{SVG}}}svg", {
        "viewBox": "0 0 1500 1160", "width": "1500", "height": "1160",
        "role": "img", "aria-labelledby": "diagram-title diagram-description",
    })

    def node(tag, attributes=None, text=None, parent=svg):
        element = ET.SubElement(parent, f"{{{SVG}}}{tag}",
                                {k.replace("_", "-"): str(v) for k, v in (attributes or {}).items()})
        if text is not None:
            element.text = text
        return element

    def label(x, y, text, size=18, fill="#243847", weight="400", anchor="start", parent=svg):
        return node("text", dict(x=x, y=y, font_family="Arial, Helvetica, sans-serif",
                                 font_size=size, fill=fill, font_weight=weight,
                                 text_anchor=anchor), text, parent)

    node("title", {"id": "diagram-title"}, "Goodjohn: Pico to 19-pin CPC keyboard connector")
    node("desc", {"id": "diagram-description"},
         "Top-view wiring guide. Adapter connector J1 uses the Bread80 CPC464 J3 contact order. "
         "Nineteen separate signal wires connect to Pico GPIO 2 through 20. "
         "Connector contact 19 is at the top and square contact 1 at the bottom. "
         "The Pico USB port carries both power and keyboard data to the PC. "
         "The CPC motherboard must be disconnected. This is not a PCB layout.")
    node("rect", dict(width=1500, height=1160, fill="white"))
    # Keep the original vector artwork and its styles, not a bitmap screenshot.
    svg.append(deepcopy(original.find(f"{{{SVG}}}style")))
    label(48, 49, "GOODJOHN", 16, "#076879", "700")
    label(48, 93, "Pico to 19-pin CPC keyboard connector", 32, weight="700")
    label(48, 124, "19 signal wires  /  RP2040 Pico or Pico H  /  component-side view", 18, "#526572")

    node("rect", dict(x=40, y=171, width=1420, height=850, rx=20,
                      fill="#f8fafb", stroke="#cdd9df", stroke_width=1.5))
    label(65, 203, "INTERFACE BOARD CONNECTIONS", 13, "#526572", "700")
    label(1435, 203, "Wiring guide - not a PCB layout or footprint template", 13,
          "#526572", anchor="end")

    # Source artwork pad centers. Both header rows use the same 18.7102 spacing.
    scale = 1.50
    source_left, source_right = 270.5741577, 401.5894775
    source_first_y, source_pitch = 121.6880493, 18.7102204
    left_x, first_y = 890.0, 254.0
    dx, dy = left_x - scale * source_left, first_y - scale * source_first_y
    right_x = dx + scale * source_right

    def pico_pin(pin):
        return (left_x, first_y + (pin - 1) * source_pitch * scale) if pin <= 20 else (
            right_x, first_y + (40 - pin) * source_pitch * scale)

    contact_x, contact_top, contact_pitch = 310, 338, 28

    def contact_y(pad):
        return contact_top + (19 - pad) * contact_pitch

    # Draw the original Pico; all original alternate-function labels are omitted.
    board_group = node("g", {"id": "pico-artwork", "transform": f"translate({dx} {dy}) scale({scale})"})
    board_group.append(deepcopy(artwork))
    center_x = dx + scale * 336.0816
    node("path", dict(d=f"M {center_x} 215 V 145 H 1250", fill="none",
                      stroke="#526572", stroke_width=3))
    node("rect", dict(x=1250, y=124, width=176, height=44, rx=7, fill="#e5edf1"))
    label(1338, 152, "PC USB port", 18, weight="700", anchor="middle")
    label(1130, 115, "power + keyboard data", 14, "#526572")

    # The adapter connector is deliberately oriented with pad 1 at its bottom.
    # Numbered contact labels, not wire colours, define the harness connections.
    node("rect", dict(x=65, y=245, width=260, height=630, rx=12,
                      fill="white", stroke="#b7c8d1", stroke_width=1.5))
    label(84, 275, "J1  /  1 x 19", 22, weight="700")
    label(84, 298, "To keyboard cable", 15, "#526572")
    label(84, 319, "contact    net     GPIO / pin", 12, "#526572")

    paths = node("g", {"id": "signal-wires", "fill": "none", "stroke-linecap": "round",
                       "stroke-linejoin": "round"})
    for wire in wires:
        pad, pin, gpio = wire["pad"], wire["pin"], wire["gpio"]
        sx, sy = pico_pin(pin)
        cy = contact_y(pad)
        color = "#087787" if wire["net"].startswith("Y") else "#7551ad"
        if pin <= 20 and wire["net"].startswith("X"):
            track_x = 515 + (gpio - 12) * 65
            d = f"M {contact_x} {cy} H {track_x} V {sy} H {sx}"
        elif pin <= 20:
            # Keep both ends horizontal; the fan is conceptual, not a trace route.
            d = f"M {contact_x} {cy} H 485 C 600 {cy}, 650 {sy}, 765 {sy} H {sx}"
        else:
            # Five GPIOs on the opposite header run outside and below the Pico.
            idx = gpio - 16
            outer_x = 1225 + idx * 34
            below_y = 900 + idx * 22
            inner_x = 380 + idx * 31 if gpio != 20 else 347
            d = (f"M {contact_x} {cy} H {inner_x} V {below_y} H {outer_x} "
                 f"V {sy} H {sx}")
        group = node("g", {"id": f"wire-j1-{pad:02}", "data-contact": pad,
                           "data-net": wire["net"], "data-gpio": gpio,
                           "data-pico-pin": pin}, parent=paths)
        node("title", text=f"J1 contact {pad}: {wire['net']} to GP{gpio}, Pico physical pin {pin}", parent=group)
        # White casing makes an unconnected crossing readable without junction dots.
        node("path", dict(d=d, stroke="#f8fafb", stroke_width=7), parent=group)
        node("path", dict(d=d, stroke=color, stroke_width=2.5), parent=group)

    # Endpoint labels sit above wires and include physical pin numbers explicitly.
    for wire in wires:
        pad, pin, gpio, net = wire["pad"], wire["pin"], wire["gpio"], wire["net"]
        sx, sy = pico_pin(pin)
        cy = contact_y(pad)
        color = "#087787" if net.startswith("Y") else "#7551ad"
        node("rect", dict(x=76, y=cy-11, width=220, height=24, rx=4,
                          fill="#edf5f6" if net.startswith("Y") else "#f3eff8"))
        label(88, cy+6, f"{pad:02}", 16, color, "700")
        label(133, cy+6, net, 16, color)
        label(189, cy+6, f"GP{gpio} / {pin:02}", 16, color)
        if pad == 1:
            node("rect", dict(x=contact_x-6, y=cy-6, width=12, height=12,
                              fill=color, stroke="white", stroke_width=1.5))
        else:
            node("circle", dict(cx=contact_x, cy=cy, r=5, fill=color, stroke="white", stroke_width=1.5))
        node("circle", dict(cx=sx, cy=sy, r=3.6, fill=color, stroke="white", stroke_width=1.1))
        lx = sx - 121 if pin <= 20 else sx + 12
        node("rect", dict(x=lx-4, y=sy-13, width=108, height=24, rx=3, fill="#f8fafb"))
        label(lx, sy+5, f"GP{gpio} / {pin:02}", 16, color, "700")

    label(center_x, 824, "Raspberry Pi Pico", 20, weight="700", anchor="middle")
    label(center_x, 846, "Labels: GPIO / physical header pin", 14, "#526572", anchor="middle")
    label(66, 909, "Square contact = pin 1", 14, "#526572")
    label(66, 932, "J1 uses Bread80 J3's contact order.", 14, "#526572")
    label(66, 955, "Shown with contact 19 at the top.", 14, "#526572")

    # Notes are part of the SVG so they survive use outside the README.
    label(49, 1056, "Y1-Y10: scan outputs", 16, "#087787", "700")
    label(294, 1056, "X1-X9: sense inputs", 16, "#7551ad", "700")
    label(544, 1056, "Crossing wires are not joined. Unmarked Pico pins are unused.", 16, "#526572")
    label(49, 1086, "Disconnect the CPC motherboard. No keyboard power or ground wire; USB supplies the Pico.", 17, weight="700")
    label(49, 1113, "Contact order checked against Bread80 CPC464 SMT J3; verify original/other keyboard revisions before wiring.", 15, "#526572")
    label(49, 1140, "Source-checked, not bench-tested. Pico artwork adapted from the supplied pico-pinout.svg. Details: docs/pinout.pdf", 13, "#526572")

    ET.indent(svg, space="  ")
    path = root_path / "docs/wiring.svg"
    ET.ElementTree(svg).write(path, encoding="utf-8", xml_declaration=True)
    return path


if __name__ == "__main__":
    from generate_pinout import ROOT, WIRES
    print(generate(ROOT, WIRES))
