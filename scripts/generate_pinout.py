#!/usr/bin/env python3
"""Generate the ASCII and vector PDF pinout from one wiring dataset.

Install scripts/requirements-docs.txt, then run from any directory.
GPIO assignments are read from firmware so regenerated sheets follow the build.
Connector nets were checked against the source revision recorded below.
"""

from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REVISION = "Revision 5 / 2026-10-06"
BREAD_REV = "bf4a6052888fef27ca01a6b0983791d7cb4e8af1"
CHERRY_REV = "588e61006bb606d08cc981467d7990c6e3104c42"
PICO_SOURCE = "https://datasheets.raspberrypi.com/pico/Pico-R3-A4-Pinout.pdf"
BREAD_SOURCE = f"https://github.com/Bread80/CPC_Keyboards/blob/{BREAD_REV}/Keyswitch_CPC464_SMT/Keyboard.kicad_pcb"
CHERRY_SOURCE = f"https://github.com/rgbwalker/Amstrad_CPC_464_new_Cherry_Keyboard/blob/{CHERRY_REV}/README.md"
CHERRY_GERBER = f"https://github.com/rgbwalker/Amstrad_CPC_464_new_Cherry_Keyboard/blob/{CHERRY_REV}/_GERBER_V1.2_/Gerber_Amstrad_Teclado_09_PCB_Amstrad_Teclado_10_THT_Con_03_2025-03-02.zip"

# Physical Pico pins in increasing order, component side up, USB at the top.
PICO_LABELS = [
    "GP0", "GP1", "GND", "GP2", "GP3", "GP4", "GP5", "GND", "GP6", "GP7",
    "GP8", "GP9", "GND", "GP10", "GP11", "GP12", "GP13", "GND", "GP14", "GP15",
    "GP16", "GP17", "GND", "GP18", "GP19", "GP20", "GP21", "GND", "GP22", "RUN",
    "GP26", "GP27", "AGND", "GP28", "ADC_VREF", "3V3(OUT)", "3V3_EN", "GND", "VSYS", "VBUS",
]
GPIO_TO_PIN = {int(label[2:]): pin for pin, label in enumerate(PICO_LABELS, 1) if label.startswith("GP")}
J3_NETS = ["X9", "Y10"] + [f"X{i}" for i in range(1, 9)] + [f"Y{i}" for i in range(9, 0, -1)]


def assignments():
    source = (ROOT / "src/board_config.h").read_text()
    nets = {}
    for name, prefix, count in (("row_gpios", "Y", 10), ("col_gpios", "X", 9)):
        match = re.search(rf"{name}\[[^]]+\]\s*=\s*\{{([^}}]+)\}}", source)
        if not match:
            raise ValueError(f"Cannot read {name} from src/board_config.h")
        gpios = [int(n.strip()) for n in match[1].split(",")]
        if len(gpios) != count:
            raise ValueError(f"Unexpected number of pins in {name}")
        nets.update({f"{prefix}{i}": gpio for i, gpio in enumerate(gpios, 1)})
    if len(set(nets.values())) != 19:
        raise ValueError("This sheet requires 19 distinct GPIOs")
    return [dict(pad=pad, net=net, gpio=nets[net], pin=GPIO_TO_PIN[nets[net]],
                 role="Sense input" if net.startswith("X") else "Scan output")
            for pad, net in enumerate(J3_NETS, 1)]


WIRES = assignments()
BY_PIN = {wire["pin"]: wire for wire in WIRES}
BY_NET = {wire["net"]: wire for wire in WIRES}
CHECKS = [
    ("Cursor Up", "Y1", "X1"), ("A", "Y9", "X6"), ("Space", "Y6", "X8"),
    ("Either Shift", "Y3", "X6"), ("DEL", "Y10", "X9"),
    ("Main Enter", "Y3", "X3"), ("Keypad Enter", "Y1", "X7"),
]


def ascii_pin_label(pin):
    wire = BY_PIN.get(pin)
    label = PICO_LABELS[pin - 1]
    return f"{label:<4} {wire['net']:<3} J3.{wire['pad']:02}" if wire else f"{label:<8} unused"


def generate_ascii():
    lines = [
        "GOODJOHN - CPC KEYBOARD TO RASPBERRY PI PICO", REVISION,
        "=" * 76,
        "TARGET: Bread80 Keyswitch_CPC464_SMT, connector J3 (19 pins).",
        "PICO: original non-wireless RP2040 Pico / Pico H; component side up.",
        "STATUS: source-checked; rgbwalker V1.2 basic typing passed (section 6).",
        "Further individual key, chord and USB hardware tests remain pending.",
        "Firmware GPIO assignments: src/board_config.h.", "",
        "WARNING: USB KEYBOARD USE ONLY. No simultaneous CPC/PC keyboard operation.",
        "DISCONNECT the keyboard from the CPC motherboard, even with CPC power off.",
        "There is no pass-through mode. Switching the CPC off is not enough.",
        "Use 19 signal wires. No keyboard VCC or GND wire is required for this matrix.",
        "Do not wire a matrix contact to 5 V, VBUS, VSYS, 3V3 or GND.",
        "Power the Pico from the PC using a USB data cable.", "",
        "  Passive keyboard          Raspberry Pi Pico                 PC",
        "  [J3: 19 contacts] -------> [GP2..GP20, as below] --- USB ---> [USB port]",
        "  No CPC motherboard connection.", "",
        "1. WIRE LIST - J3 PAD ORDER", "-" * 76,
        "J3 pad   Matrix net   Pico GPIO   Pico PHYSICAL pin   Function",
    ]
    for w in WIRES:
        lines.append(f"  {w['pad']:02}       {w['net']:<4}          GP{w['gpio']:<2}             {w['pin']:02}           {w['role']}")
    lines += ["", "GPIO numbers and physical header pin numbers are different.",
              "Example: J3 pad 1 -> GP20 -> physical Pico pin 26 (NOT pin 20).", "",
              "J3 orientation: with keyboard keys facing you, cursor keys at upper",
              "right, J3 is the single vertical row at the far left. On the inspected",
              "PCB, pad 1 is square and at the Esc end; pad 19 is at the Caps end.",
              "Locate the square copper pad before fitting a cable. The solder side",
              "is mirrored; follow pad numbers, never an assumed cable color order.", "",
              "       Esc/rear end", "         [01]  square pad", "         (02)",
              "         (03)", "          ...", "         (19)", "       Caps/front end", "",
              "Leave LK1, LK2, LK3 and bonus-switch links LK4, LK5, LK6 OPEN.",
              "LK3 would join X8 and X9. J1/J2 use different pin orders.", "",
              "2. PICO TOP VIEW - USB AT TOP, COMPONENTS FACING YOU", "-" * 76,
              "                              USB to PC", "                           +----USB----+",
              "            GPIO/net/J3    |           |   GPIO/net/J3"]
    for left in range(1, 21):
        right = 41 - left
        lines.append(f" {ascii_pin_label(left):>22} {left:02} |           | {right:02} {ascii_pin_label(right)}")
    lines += ["                           +-----------+", "                    SWD pads are not used.",
              "'unused' = leave unconnected for this keyboard harness.",
              "All numbers next to the board outline are PHYSICAL header pin numbers.", "",
              "3. BUILD AND ASSEMBLE", "-" * 76,
              "1) Disconnect all power. Identify the board revision and J3 pad 1.",
              "2) Open the links listed above. Fit Pico headers if needed.",
              "3) Run 19 insulated wires using the wire list. Label both cable ends.",
              "   Keep the prototype cable short; verify every connection with a meter.",
              "4) Check the switch pairs below and check for unintended adjacent shorts.",
              "5) Build/flash build/goodjohn.uf2, then connect Pico USB to the PC.",
              "   For BOOTSEL flashing, hold BOOTSEL while plugging in USB and copy",
              "   the UF2 to RPI-RP2. No existing CPC electronics should be attached.", "",
              "Bread80 SMT with every diode present and oriented correctly:",
              "  cmake -S . -B build -DGOODJOHN_MATRIX_HAS_DIODES=ON",
              "  cmake --build build --parallel", "",
              "Original membrane / rgbwalker / Bread80 tactile / uncertain diodes:",
              "  cmake -S . -B build -DGOODJOHN_MATRIX_HAS_DIODES=OFF",
              "  cmake --build build --parallel",
              "These commands reconfigure an existing build; see README.md for SDK setup.", "",
              "4. UNPOWERED SWITCH TESTS", "-" * 76,
              "Disconnect the keyboard from both Pico and CPC for these switch tests.",
              "Key             Matrix pair        J3 pad pair     Pico physical pair"]
    for key, row, col in CHECKS:
        a, b = BY_NET[row], BY_NET[col]
        lines.append(f"{key:<15} {row + '/' + col:<18} {str(a['pad']) + '/' + str(b['pad']):<15} {a['pin']}/{b['pin']}")
    lines += ["", "For SMT diodes, use diode mode with red probe on X and black on Y.",
              "Press the key: forward conduction. Release it: open. Reverse polarity",
              "should block on a diode board. On a plain switch board, continuity",
              "works in either direction. A continuity beeper alone may miss a diode.", "",
              "Scan current: 3.3 V pull-up -> X -> closed switch -> diode -> selected Y.",
              "              X ---- switch ---- |>| ---- Y", "                                  cathode toward Y",
              "Only the selected Y sinks low; all other Y lines float. X lines are inputs.",
              "The pull-ups are internal to the Pico; no external matrix supply is needed.", "",
              "5. FIRST USB TEST", "-" * 76,
              "Check every key and release, both Shift keys, Ctrl, COPY, both Enter keys",
              "and DEL. COPY sends Alt; DEL sends Backspace; CLR sends forward Delete.",
              "Set PC Num Lock for numeric keypad digits. Both Shifts share one contact.",
              "Test chords: diode-less matrices suppress ambiguous new keys, so some",
              "chords will be blocked. Do not disable that filter to cure missing keys.",
              "Above six regular keys, HID reports ErrorRollOver until keys are released.",
              "Exact shifted CPC symbols depend on the PC layout; no Fn layer yet.",
              "V1.2 digits, letters, Esc and main Enter passed; see section 6.",
              "Other keys/chords, USB suspend current and suspend/resume need checks.", "",
              "6. RGBWALKER V1.2 - CONNECTOR AND DIRECT-WIRE BRING-UP", "-" * 76,
              "DO NOT treat J3's table as a verified pinout for every 20-pin keyboard.",
              "V1.2 Gerbers: CP002_THT and CP002_SMD contacts 1..19 match each other.",
              "Count square pad as 1 at the Esc end, downward toward Shift.",
              "  contacts 1/2: isolated DEL switch; expected harness GP20/GP11",
              "  contacts 3..10: X1..X8; expected harness GP12..GP19",
              "  contacts 11..19: Y9..Y1; expected harness GP10..GP2",
              "  contact 20: isolated from the matrix in this revision; leave disconnected.",
              "With Pico disconnected, switch pairs are: 1 = 3/11, 2 = 4/11, Esc = 5/11.",
              "The service drawing reverses the two DEL wire names relative to Bread80;",
              "that does not affect the isolated diode-less DEL switch. Keep diodes OFF.", "",
              "Unplug USB before each wiring change or meter check. Start directly:",
              "  keyboard 3  -> Pico PHYSICAL 16 (GP12)",
              "  keyboard 11 -> Pico PHYSICAL 14 (GP10)",
              "Each pad-to-pad wire path must beep WITHOUT pressing a key. Then power",
              "by USB and press top-row 1. This direct test passed on 2026-10-06.",
              "Bypassing the previous ribbon/jumper assembly restored 1; its exact",
              "fault has not been identified. Firmware and keymap changes were not needed.",
              "Next add keyboard 4 -> Pico 17 (GP13) for 2, then 5 -> Pico 19 (GP14)",
              "for Esc. Check each wire before USB power. Esc prints no character.",
              "Then add contacts 12..16 -> physical pins 12,11,10,9,7 for digits 1..0.",
              "Complete contacts 1..19 using section 1; keep contact 20 disconnected.",
              "USER-CONFIRMED, 2026-10-06: completed 19-wire direct harness passes",
              "1234567890, qwertyuiop, asdfghjkl, zxcvbnm, Esc and main Enter.",
              "Individual remaining keys, modifiers, chords and USB tests are pending.",
              "Before reusing an adapter, map and label every wire with a meter.",
              "For switch-pair identification, disconnect the keyboard from the Pico:",
              "an unpowered Pico can still provide other paths through its circuitry.",
              "Full procedure and test status: docs/wiring.md.", "",
              "Bread80 J1, CPC464 links: see docs/pinout-dual-ribbon.txt and .pdf.",
              "Bread80 tactile, J2 modular and CPC6128 need their own",
              "connector mapping. An 18-wire harness needs explicit X8/X9 handling.", "",
              "7. SOURCES AND REGENERATION", "-" * 76,
              f"Bread80 reference: {BREAD_REV}", BREAD_SOURCE,
              f"rgbwalker reference: {CHERRY_REV}", CHERRY_SOURCE,
              "rgbwalker V1.2 fabrication archive:", CHERRY_GERBER,
              "Pico physical header reference:", PICO_SOURCE, "",
              "The PDF uses original vector drawings; it includes no copied PCB photos.",
              "Regenerate both sheets:",
              "  python3 -m pip install -r scripts/requirements-docs.txt",
              "  python3 scripts/generate_pinout.py", ""]
    text = "\n".join(lines)
    assert text.isascii()
    (DOCS / "pinout.txt").write_text(text, encoding="ascii")


PAGE_W, PAGE_H = A4
MARGIN = 38
WIDTH = PAGE_W - 2 * MARGIN
INK = colors.HexColor("#182c3a")
MUTED = colors.HexColor("#526572")
SCAN = colors.HexColor("#076879")
SENSE = colors.HexColor("#5a429a")
PALE = colors.HexColor("#edf3f6")
AMBER = colors.HexColor("#fff3db")


class Sheet:
    def __init__(self):
        self.c = canvas.Canvas(str(DOCS / "pinout.pdf"), pagesize=A4, invariant=1, pageCompression=1)
        self.c.setTitle("Goodjohn - CPC keyboard to Raspberry Pi Pico pinout")
        self.c.setAuthor("Goodjohn project")
        self.c.setCreator("Goodjohn pinout generator / ReportLab")
        self.c.setSubject("Bread80 CPC464 SMT J3 wiring, Pico top view, assembly and connector checks")
        self.page = 0

    def paragraph(self, text, y, size=10, color=INK, x=MARGIN, width=WIDTH, gap=8):
        style = ParagraphStyle("body", fontName="Helvetica", fontSize=size,
                               leading=size * 1.4, textColor=color, alignment=TA_LEFT)
        p = Paragraph(text, style)
        _, height = p.wrap(width, PAGE_H)
        if y - height < 47:
            raise ValueError(f"Page {self.page} overflows: {text[:70]}")
        p.drawOn(self.c, x, y - height)
        return y - height - gap

    def heading(self, text, y):
        return self.paragraph(f"<b>{text}</b>", y, 12, SCAN, gap=9)

    def banner(self, text, y, fill=AMBER):
        p = Paragraph(text, ParagraphStyle("banner", fontName="Helvetica", fontSize=10,
                                           leading=14, textColor=INK))
        _, h = p.wrap(WIDTH - 22, PAGE_H)
        self.c.setFillColor(fill)
        self.c.roundRect(MARGIN, y - h - 18, WIDTH, h + 18, 5, fill=1, stroke=0)
        p.drawOn(self.c, MARGIN + 11, y - h - 9)
        return y - h - 30

    def table(self, rows, widths, y, row_height=19, size=9):
        t = Table(rows, colWidths=widths, rowHeights=row_height)
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), size),
            ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#c6d2d9")),
        ]))
        _, height = t.wrap(WIDTH, PAGE_H)
        if y - height < 47:
            raise ValueError(f"Table overflows page {self.page}")
        t.drawOn(self.c, MARGIN, y - height)
        return y - height - 12

    def begin(self, title, subtitle):
        if self.page:
            self.c.showPage()
        self.page += 1
        c = self.c
        c.setFillColor(SCAN)
        c.rect(0, PAGE_H - 10, PAGE_W, 10, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN, PAGE_H - 33, "GOODJOHN  /  WORKBENCH REFERENCE")
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 23)
        c.drawString(MARGIN, PAGE_H - 64, title)
        self.paragraph(subtitle, PAGE_H - 77, 9, MUTED)
        c.setStrokeColor(colors.HexColor("#c6d2d9"))
        c.line(MARGIN, 36, PAGE_W - MARGIN, 36)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(MARGIN, 23, REVISION + "  |  V1.2 basic typing passed; further tests pending")
        c.drawRightString(PAGE_W - MARGIN, 23, f"{self.page} / 4")
        return PAGE_H - 113

    def quick_reference(self):
        y = self.begin("Keyboard-to-Pico wire list", "Bread80 CPC464 SMT / J3 19-pin connector / original RP2040 Pico or Pico H")
        y = self.banner("<b>USB keyboard use only.</b> Physically disconnect the keyboard from the CPC motherboard, even when off. <b>No simultaneous CPC/PC keyboard operation.</b> Use 19 signal wires only; no matrix power or ground. Power the Pico by USB.", y)
        c = self.c
        labels = ["Keyboard J3", "Pico GPIO", "PC USB port"]
        box_w = 145
        for i, label in enumerate(labels):
            x = MARGIN + i * (WIDTH - box_w) / 2
            c.setFillColor(PALE)
            c.roundRect(x, y - 31, box_w, 31, 4, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(x + box_w / 2, y - 20, label)
            if i < 2:
                start = x + box_w + 3
                end = MARGIN + (i + 1) * (WIDTH - box_w) / 2 - 4
                c.setStrokeColor(SCAN)
                c.line(start, y - 16, end, y - 16)
                c.line(end - 4, y - 12, end, y - 16)
                c.line(end - 4, y - 20, end, y - 16)
        y -= 43
        rows = [["J3 pad", "Matrix net", "Pico GPIO", "Pico header pin", "Signal role"]]
        for w in WIRES:
            rows.append([f"{w['pad']:02}", w['net'], f"GP{w['gpio']}", f"{w['pin']:02}", w['role']])
        y = self.table(rows, [62, 87, 90, 117, WIDTH - 356], y)
        y = self.paragraph("<b>Header pin is the physical pin number.</b> For example, J3 pad 1 connects to <b>GP20 on Pico pin 26</b>, not to Pico pin 20.", y)
        y = self.heading("Identify J3 before wiring", y)
        y = self.paragraph("With keys facing you and cursor keys at upper right, J3 is the single vertical row at the keyboard's far left. On the inspected PCB, <b>pad 1 is square at the Esc end</b>; pad 19 is at the Caps end. The solder-side view is mirrored.", y)
        y = self.paragraph("Leave <b>LK1, LK2, LK3 and LK4-LK6 open</b> for this prototype. LK3 joins X8/X9; the last three links serve the unused bonus keys. <b>J1 and J2 have different pin orders.</b>", y)
        self.paragraph("J3 nets: Bread80 PCB revision " + BREAD_REV[:12] + ". Firmware pin assignments: src/board_config.h. See page 4 for rgbwalker V1.2 checks and the first hardware test.", y, 8.5, MUTED)

    def pico_view(self):
        y = self.begin("Pico header orientation", "Top view: components and BOOTSEL button facing you, USB connector at the top. Not to scale.")
        y = self.banner("Numbers beside the board are <b>physical header pins</b>. Labels show GPIO / matrix net / J3 pad. Anything marked <b>unused</b> stays unconnected in this keyboard harness.", y, PALE)
        c = self.c
        top = y - 25
        first = top - 30
        pitch = 18.5
        bottom = first - pitch * 19 - 24
        left_x, right_x = 250, 345
        c.setFillColor(colors.HexColor("#e9f1ec"))
        c.setStrokeColor(SCAN)
        c.roundRect(left_x - 10, bottom, right_x - left_x + 20, top - bottom, 10, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#c6d2d9"))
        c.roundRect(275, top - 13, 45, 30, 3, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(INK)
        c.drawCentredString(297.5, top + 25, "USB to PC")
        c.setFont("Helvetica", 8)
        c.drawCentredString(297.5, first - 55, "BOOTSEL")
        c.setFillColor(colors.HexColor("#b9c9c0"))
        c.roundRect(281, first - 85, 33, 20, 3, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(297.5, first - 175, "RP2040")
        c.setFont("Helvetica", 8)
        c.drawCentredString(297.5, first - 191, "Pico / Pico H")
        for left in range(1, 21):
            yy = first - (left - 1) * pitch
            for pin, x, is_left in ((left, left_x, True), (41 - left, right_x, False)):
                w = BY_PIN.get(pin)
                color = (SCAN if w["net"].startswith("Y") else SENSE) if w else MUTED
                c.setFillColor(color)
                if pin == 1:
                    c.rect(x - 3.5, yy - 3.5, 7, 7, fill=1, stroke=0)
                else:
                    c.circle(x, yy, 3.5, fill=1, stroke=0)
                c.setFont("Helvetica-Bold", 9)
                if is_left:
                    c.drawRightString(x - 12, yy - 3, f"{pin:02}")
                else:
                    c.drawString(x + 12, yy - 3, f"{pin:02}")
                c.setFont("Helvetica", 9)
                label = ascii_pin_label(pin).replace("J3.", "J3 ")
                if is_left:
                    c.drawRightString(x - 36, yy - 3, label)
                else:
                    c.drawString(x + 36, yy - 3, label)
        y = bottom - 22
        y = self.paragraph("<font color='#076879'><b>Y = scan outputs</b></font> &nbsp;&nbsp; <font color='#5a429a'><b>X = sense inputs</b></font> &nbsp;&nbsp; Grey = unused", y, 10)
        y = self.heading("Three details that prevent wiring mistakes", y - 5)
        for text in [
            "<b>Count down the left side: 1 to 20.</b> The right side counts up from 21 at the bottom to 40 at the top. Ground pins interrupt the GPIO sequence.",
            "<b>No matrix supply pin:</b> X inputs use the Pico's internal 3.3 V pull-ups. The USB cable powers the Pico; the passive keyboard needs only the 19 signal connections.",
            "<b>Do not join X8 and X9 in this harness.</b> X9 is dedicated to DEL. Both Shift switches share Y3/X6 and cannot be distinguished by firmware.",
        ]:
            y = self.paragraph(text, y, 9.5)
        self.paragraph(f'Physical numbering checked against <link href="{PICO_SOURCE}" color="#076879">Raspberry Pi\'s official Pico pinout PDF</link>. The diagram above is an original drawing for this project.', y, 8.5, MUTED)

    def assembly(self):
        y = self.begin("Assemble and verify", "Work with USB unplugged during wiring and meter checks. Connect only the passive keyboard.")
        for text in [
            "<b>1. Prepare:</b> identify the exact board and J3 pad 1. Open LK1-LK6. Fit Pico headers if needed. Use insulated wires or a labeled breakout harness; keep the first cable short.",
            "<b>2. Wire:</b> follow page 1 one contact at a time. Check every cable endpoint and look for unintended adjacent shorts. Do not rely on ribbon-wire colors or a mirrored photograph.",
            "<b>3. Test contacts:</b> disconnect the keyboard from both Pico and CPC; check the pairs below. On a diode board, place the red meter probe on X and black on Y, using diode mode.",
        ]:
            y = self.paragraph(text, y)
        rows = [["Key held", "Y / X nets", "J3 pads", "Pico header pins"]]
        for key, row, col in CHECKS:
            a, b = BY_NET[row], BY_NET[col]
            rows.append([key, f"{row} / {col}", f"{a['pad']} / {b['pad']}", f"{a['pin']} / {b['pin']}"])
        y = self.table(rows, [135, 113, 105, WIDTH - 353], y, 22)
        y = self.paragraph("A pressed key should conduct; releasing it should open the path. A diode blocks the reverse direction. A plain switch conducts either way. A continuity beeper may not detect the diode path reliably.", y, 9.5)
        y = self.banner("<b>Current path:</b> internal 3.3 V pull-up &rarr; X &rarr; closed switch &rarr; diode &rarr; selected Y.<br/>Diode cathode faces Y. Only the selected Y is driven low; inactive Y pins float.", y, PALE)
        y = self.heading("Choose the correct scan option", y)
        y = self.paragraph("<b>Bread80 SMT, all diodes verified:</b> set the option ON. <b>rgbwalker, membrane, tactile, or uncertain diodes:</b> keep it OFF. These commands assume the SDK build is already configured; see README.md for initial setup.", y, 9.5)
        for code in ("cmake -S . -B build -DGOODJOHN_MATRIX_HAS_DIODES=ON", "cmake --build build --parallel"):
            y = self.paragraph(f'<font name="Courier">{code}</font>', y, 8.6, gap=3)
        y = self.paragraph("Use <b>OFF</b> instead of ON for a matrix without verified diodes.", y + 1, 9)
        y = self.heading("Flash, then test on the PC", y)
        y = self.paragraph("Hold BOOTSEL while connecting the Pico, then copy <b>build/goodjohn.uf2</b> to RPI-RP2. Use a USB data cable. Check every key and release, modifiers, DEL and both Enter keys. COPY sends Alt; DEL sends Backspace; CLR sends forward Delete. Set the PC's Num Lock for keypad digits.", y, 9.5)
        y = self.paragraph("If one group of keys fails, recheck its X/Y wire and diode orientation. If only chords fail on a board without diodes, ghost suppression may be blocking ambiguity. More than six regular keys produces HID ErrorRollOver. Shifted symbols follow the PC layout; there is no Fn layer yet.", y, 9.5)
        self.paragraph("V1.2 digits, all letter rows, Esc and main Enter passed with the completed direct harness; see page 4. Remaining keys, chords, cable settling, USB reconnect and suspend still need tests. No USB remote wakeup or low-power suspend implementation is provided yet.", y, 8.5, MUTED)

    def variants(self):
        y = self.begin("Other boards and source notes", "The logical CPC key matrix is shared; connector order and jumper routing are not universal.")
        y = self.banner("<b>rgbwalker V1.2: basic typing passed (2026-10-06).</b> User confirmed digits, all letter rows, Esc and main Enter with the completed 19-wire direct harness.", y)
        y = self.paragraph("V1.2 Gerbers connect CP002_THT and CP002_SMD contacts 1-19 in the same order; contact 20 is isolated from the matrix. Count the <b>square pad as 1 at the Esc end</b>, toward Shift. Check other revisions separately.", y, 9.5)
        rows = [
            ["Expected contact(s)", "Expected switch lines", "Pico harness, if confirmed"],
            ["1 and 2", "Isolated DEL switch", "GP20 and GP11"],
            ["3 through 10", "X1 through X8", "GP12 through GP19"],
            ["11 through 19", "Y9 through Y1", "GP10 down through GP2"],
            ["20", "No matrix connection (V1.2)", "Leave isolated"],
        ]
        y = self.table(rows, [137, 164, WIDTH - 301], y, 24, 9)
        y = self.paragraph("<b>Start directly:</b> keyboard <b>3 to Pico physical 16 (GP12)</b>; keyboard <b>11 to physical 14 (GP10)</b>. With USB unplugged, each wire must beep pad-to-pad without a key held. Connect USB: top-row 1 should type 1. Bypassing the earlier ribbon/jumper assembly restored this; its exact fault is unresolved.", y, 9.5)
        y = self.paragraph("Unplug USB, then add <b>4 to physical 17 (GP13)</b> for 2; next <b>5 to physical 19 (GP14)</b> for Esc. Check each wire before power. Esc prints no character. Complete contacts 1-19 using page 1, leave 20 disconnected, and keep <b>GOODJOHN_MATRIX_HAS_DIODES=OFF</b>. Details: docs/wiring.md.", y, 9.5)
        y = self.heading("Bread80 alternatives", y)
        y = self.paragraph("<b>J1 membrane, CPC464 links:</b> see the separate <b>docs/pinout-dual-ribbon.pdf</b> and wiring-dual-ribbon.svg. <b>J2 modular:</b> not mapped here. <b>Tactile:</b> different connectors, no diodes. <b>CPC6128 SMT:</b> design-stage board; not a validated adapter target.", y)
        y = self.paragraph("An 18-wire adaptation must handle the shared X8/X9 net explicitly; simply omitting X9 loses DEL.", y, 9.5)
        y = self.heading("Source records", y)
        references = [
            ("Bread80 CPC464 SMT KiCad PCB", BREAD_SOURCE,
             f"Revision {BREAD_REV}. J3 pad nets, square pad 1, connector placement, diode cathodes and switch coordinates were inspected."),
            ("rgbwalker V1.2 fabrication archive", CHERRY_GERBER,
             f"Revision {CHERRY_REV}. Copper/plated-hole tracing checks THT/SMD correspondence, unused contact 20, and switch pairs: 1 = 3/11, 2 = 4/11, Esc = 5/11."),
            ("Raspberry Pi official Pico pinout", PICO_SOURCE,
             "Pico-R3-A4-Pinout.pdf. Used to check the 40 physical header positions and power/ground labels. Target is the original non-wireless RP2040 Pico/Pico H."),
        ]
        for label, url, detail in references:
            y = self.paragraph(f'<b><link href="{url}" color="#076879">{label}</link></b><br/>{escape(detail)}', y, 9)
        y = self.heading("Files and regeneration", y)
        y = self.paragraph("The companion ASCII sheet is <b>docs/pinout.txt</b>. The generator reads the firmware GPIO arrays in <b>src/board_config.h</b> and produces both formats from one wiring dataset. These are original vector drawings, not scaled PCB templates.", y, 9)
        for code in ("python3 -m pip install -r scripts/requirements-docs.txt", "python3 scripts/generate_pinout.py"):
            y = self.paragraph(f'<font name="Courier">{code}</font>', y, 8.6, gap=3)

    def save(self):
        self.quick_reference()
        self.pico_view()
        self.assembly()
        self.variants()
        self.c.save()


if __name__ == "__main__":
    generate_ascii()
    Sheet().save()
    print("Generated docs/pinout.txt and docs/pinout.pdf")
