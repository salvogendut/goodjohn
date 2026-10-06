#!/usr/bin/env python3
"""Recreate the v1 carrier schematic/placement; routing is a separate step.

Requires KiCad 10 pcbnew for --pcb; --libraries/--schematic use Python stdlib.
Do not rerun over manual edits without reviewing the resulting diff.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import re
import uuid
import xml.etree.ElementTree as ET

from sexpr import Atom, child, children, dumps, loads

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'hardware/pico-carrier-v1'
STEM = 'goodjohn-carrier'
LIB = 'Goodjohn'
NAMESPACE = uuid.UUID('5f866819-2e28-48cf-ab49-0e9884814621')

# Frozen v1 connector definition; verify.py checks it against firmware and docs.
INLINE = ['X9', 'Y10'] + [f'X{i}' for i in range(1, 9)] + [f'Y{i}' for i in range(9, 0, -1)]
RIBBON_A = ['Y10', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X9', None]
RIBBON_B = ['X8', 'Y9', 'Y8', 'Y7', 'Y6', 'Y5', 'Y4', 'Y3', 'Y2', 'Y1']
PICO_GPIO_PINS = {2: 4, 3: 5, 4: 6, 5: 7, 6: 9, 7: 10, 8: 11, 9: 12,
                  10: 14, 11: 15, 12: 16, 13: 17, 14: 19, 15: 20,
                  16: 21, 17: 22, 18: 24, 19: 25, 20: 26}
GPIO = {**{f'Y{i}': i + 1 for i in range(1, 11)},
        **{f'X{i}': i + 11 for i in range(1, 10)}}
PICO = {str(PICO_GPIO_PINS[gpio]): net for net, gpio in GPIO.items()}
PICO.update({str(pin): 'GND' for pin in [3, 8, 13, 18, 23, 28, 38]})
PIN_NETS = {'U1': PICO,
            'J1': {str(i): n for i, n in enumerate(INLINE, 1)},
            'J2': {str(i): n for i, n in enumerate(RIBBON_A, 1) if n},
            'J3': {str(i): n for i, n in enumerate(RIBBON_B, 1)}}
FOOTPRINTS = {
    'U1': 'Pico_Socketed_RP2040',
    'J1': 'PinHeader_1x19_P2.54mm_Vertical',
    'J2': 'PinHeader_1x10_P2.54mm_Vertical',
    'J3': 'PinHeader_1x10_P2.54mm_Vertical',
    **{f'H{i}': 'MountingHole_3.2mm_M3' for i in range(1, 5)},
}
SYMBOLS = {'U1': 'RaspberryPi_Pico', 'J1': 'Conn_01x19',
           'J2': 'Conn_01x10', 'J3': 'Conn_01x10',
           **{f'H{i}': 'MountingHole' for i in range(1, 5)}}
VALUES = {'U1': 'RaspberryPi_Pico', 'J1': 'CPC464_INLINE_19',
          'J2': 'RIBBON_A_ODD', 'J3': 'RIBBON_B_EVEN',
          **{f'H{i}': 'M3_NPTH' for i in range(1, 5)}}
SCHEM_POS = {'U1': (68.58, 96.52), 'J1': (165.1, 101.6),
             'J2': (241.3, 73.66), 'J3': (241.3, 127),
             **{f'H{i}': (139.7 + i * 20.32, 154.94) for i in range(1, 5)}}
# Top view: USB at the upper edge; J1 pin 1 at bottom; J2/J3 pin 1 at top.
PCB_POS = {'U1': (110.16, 103.048, 0), 'J1': (173.66, 155.88, 180),
           'J2': (151.816, 115.24, 0), 'J3': (143.18, 115.24, 0),
           'H1': (104, 104, 0), 'H2': (176, 104, 0),
           'H3': (104, 162, 0), 'H4': (176, 162, 0)}
OUTLINE = (100, 100, 180, 166)


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def q(value):
    return json.dumps(str(value))


def lib_symbols():
    return children(loads((DEST / 'libraries/Goodjohn.kicad_sym').read_text()), 'symbol')


def libraries(source):
    """Vendor only the symbols/footprints needed, preserving library provenance."""
    all_symbols = []
    for library, names in [('MCU_Module', ['RaspberryPi_Pico']),
                           ('Connector_Generic', ['Conn_01x10', 'Conn_01x19']),
                           ('Mechanical', ['MountingHole'])]:
        parsed = loads((source / 'symbols' / f'{library}.kicad_sym').read_text())
        all_symbols.extend(s for s in children(parsed, 'symbol') if s[1] in names)
    assert len(all_symbols) == 4
    (DEST / 'libraries/Goodjohn.kicad_sym').write_text(
        '(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n' +
        '\n'.join(dumps(s) for s in all_symbols) + '\n)\n')
    for library, original, name in [
        ('Module', 'RaspberryPi_Pico_Common_THT', 'Pico_Socketed_RP2040'),
        ('Connector_PinHeader_2.54mm', 'PinHeader_1x19_P2.54mm_Vertical', 'PinHeader_1x19_P2.54mm_Vertical'),
        ('Connector_PinHeader_2.54mm', 'PinHeader_1x10_P2.54mm_Vertical', 'PinHeader_1x10_P2.54mm_Vertical'),
        ('MountingHole', 'MountingHole_3.2mm_M3', 'MountingHole_3.2mm_M3'),
    ]:
        fp = loads((source / 'footprints' / f'{library}.pretty' / f'{original}.kicad_mod').read_text())
        fp[1] = name
        if name == 'Pico_Socketed_RP2040':
            # RP2040 Pico only, not Pico W: remove the common footprint's
            # antenna rule area. USB courtyard and physical pad geometry stay.
            fp[:] = [n for n in fp if not (isinstance(n, list) and (
                n[0] == 'group' or
                n[0] == 'zone' and child(n, 'name') == [Atom('name'), 'Antenna Copper Keep Out'] or
                n[0] == 'fp_text' and n[2] in ['Possible Antenna', 'Keep Out']))]
            child(fp, 'descr')[1] = 'RP2040 Pico on two 1x20 2.54mm sockets; rows 17.78mm apart. Derived from KiCad RaspberryPi_Pico_Common_THT.'
            for model in children(fp, 'model'):
                if model[1].endswith('RaspberryPi_Pico_PinSockets_H8.50mm.step'):
                    model[:] = [n for n in model if not (isinstance(n, list) and n[0] == 'hide')]
                elif model[1].endswith('RaspberryPi_Pico_H.step'):
                    child(child(model, 'offset'), 'xyz')[3] = Atom('8.5')
            for prop in children(fp, 'property'):
                if prop[1] == 'Value':
                    prop[2] = name
        (DEST / 'libraries/Goodjohn.pretty' / f'{name}.kicad_mod').write_text(dumps(fp) + '\n')
    (DEST / 'sym-lib-table').write_text('(sym_lib_table (version 7)\n (lib (name "Goodjohn") (type "KiCad") (uri "${KIPRJMOD}/libraries/Goodjohn.kicad_sym") (options "") (descr "Project symbols; see libraries/README.md"))\n)\n')
    (DEST / 'fp-lib-table').write_text('(fp_lib_table (version 7)\n (lib (name "Goodjohn") (type "KiCad") (uri "${KIPRJMOD}/libraries/Goodjohn.pretty") (options "") (descr "Project footprints; see libraries/README.md"))\n)\n')


def schematic():
    symbols = lib_symbols()
    cache = []
    for s in symbols:
        s = copy.deepcopy(s)
        s[1] = f'{LIB}:{s[1]}'
        cache.append(dumps(s))
    out = [f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {q(uid("root"))}) (paper "A4")',
           '(title_block (title "Goodjohn - CPC464 USB keyboard carrier") (date "2026-10-06") (rev "1.0-prototype") (company "salvogendut / Goodjohn") (comment 1 "RP2040 Pico only - USB keyboard use only") (comment 2 "Disconnect keyboard from CPC motherboard, even when CPC is off"))',
           '(lib_symbols\n' + '\n'.join(cache) + ')']
    for ref, symbol_name in SYMBOLS.items():
        x, y = SCHEM_POS[ref]
        symbol = next(s for s in symbols if s[1] == symbol_name)
        in_bom = 'no' if ref.startswith('H') else 'yes'
        instance = [f'(symbol (lib_id {q(LIB + ":" + symbol_name)}) (at {x} {y} 0) (unit 1) (in_bom {in_bom}) (on_board yes) (dnp no) (uuid {q(uid(ref))})']
        # Keep each symbol's library field placement; connector values get room.
        for name, val in [('Reference', ref), ('Value', VALUES[ref]), ('Footprint', f'{LIB}:{FOOTPRINTS[ref]}'), ('Datasheet', '')]:
            prop = next(p for p in children(symbol, 'property') if p[1] == name)
            at = child(prop, 'at')
            px, py = x + float(at[1]), y - float(at[2])
            hidden = '(hide yes)' if name in ['Footprint', 'Datasheet'] else ''
            instance.append(f'(property {q(name)} {q(val)} (at {px} {py} 0) {hidden} (effects (font (size 1.27 1.27)) (justify left)))')
        pins = [p for unit in children(symbol, 'symbol') for p in children(unit, 'pin')]
        handled_positions = set()
        for pin in pins:
            number = child(pin, 'number')[1]
            instance.append(f'(pin {q(number)} (uuid {q(uid(ref + "." + number))}))')
            px, py, angle = map(float, child(pin, 'at')[1:])
            px, py = round(x + px, 6), round(y - py, 6)
            if (px, py) in handled_positions:
                continue
            handled_positions.add((px, py))
            net = PIN_NETS.get(ref, {}).get(number)
            if net:
                ex = round(px - math.cos(math.radians(angle)) * 7.62, 6)
                ey = round(py + math.sin(math.radians(angle)) * 7.62, 6)
                out.append(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid {q(uid(ref + number + "wire"))}))')
                out.append(f'(label {q(net)} (at {ex} {ey} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {q(uid(ref + number + "label"))}))')
            else:
                out.append(f'(no_connect (at {px} {py}) (uuid {q(uid(ref + number + "nc"))}))')
        instance.append(f'(instances (project {q(STEM)} (path {q("/" + uid("root"))} (reference {q(ref)}) (unit 1)))))')
        out.extend(instance)
    notes = [
        (25.4, 22.86, 2, 'GOODJOHN / CPC464 USB KEYBOARD CARRIER'),
        (25.4, 30.48, 1.5, 'USB KEYBOARD ONLY - DISCONNECT CPC MOTHERBOARD, EVEN WHEN POWERED OFF.'),
        (25.4, 36.83, 1.27, 'Use J1 OR J2 + J3 for one keyboard. No CPC pass-through; no keyboard supply connection.'),
        (25.4, 148.59, 1.27, 'U1: original RP2040 Pico / Pico H on two 1x20 sockets.\nPC USB data cable supplies power via the Pico USB socket.\nOnly GND is used on the carrier; VBUS / VSYS / 3V3 stay isolated.\nGP2..GP11 scan Y1..Y10; GP12..GP20 sense X1..X9.\nUnselected rows are inputs; X inputs use Pico pull-ups.'),
        (132.08, 52.07, 1.27, 'J1: INLINE 19 CONTACTS\nrgbwalker V1.2 / Bread80 J3 / original PCB-style CPC464\nContact 1 = X9; optional keyboard contact 20 stays unused.'),
        (208.28, 48.26, 1.27, 'BREAD80 CPC464 SMT J1\nJ2 = A, odd keyboard pads 1..19\nJ3 = B, even keyboard pads 2..20'),
        (208.28, 96.52, 1.27, 'A10 / keyboard J1.19 is NC.\nB10 / keyboard J1.20 is Y1.\nLK1: 1-2; LK2: 1-2; LK3 open.\nBonus links open.'),
        (25.4, 176.53, 1.27, 'H1..H4: 3.2mm unplated holes for M3 standoffs.\nAll keyboard contacts are signals: never attach power or GND.\nPrototype: electrical/design checks do not replace bench testing.'),
    ]
    for i, (x, y, size, message) in enumerate(notes):
        out.append(f'(text {q(message)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {q(uid("note" + str(i)))}))')
    out.append('(embedded_fonts no))')
    (DEST / f'{STEM}.kicad_sch').write_text('\n'.join(out) + '\n')
    project = {
        'meta': {'filename': f'{STEM}.kicad_pro', 'version': 3},
        'board': {'design_settings': {'meta': {'version': 2}, 'rules': {'min_clearance': 0.25, 'min_track_width': 0.25,
                   'min_via_diameter': 0.8, 'min_through_hole_diameter': 0.3,
                   'min_via_annular_width': 0.2, 'min_hole_clearance': 0.25,
                   'min_copper_edge_clearance': 0.5, 'min_silk_clearance': 0.15,
                   'min_text_height': 0.8, 'min_text_thickness': 0.12},
                   'track_widths': [0, 0.25, 0.3, 0.5],
                   'via_dimensions': [{'diameter': 0.8, 'drill': 0.4}]}},
        'net_settings': {'classes': [{'name': 'Default', 'clearance': 0.25,
             'track_width': 0.3, 'via_diameter': 0.8, 'via_drill': 0.4,
             'microvia_diameter': 0.3, 'microvia_drill': 0.1,
             'diff_pair_width': 0.25, 'diff_pair_gap': 0.25, 'diff_pair_via_gap': 0.25}], 'meta': {'version': 5}},
    }
    (DEST / f'{STEM}.kicad_pro').write_text(json.dumps(project, indent=2) + '\n')


def pcb():
    import pcbnew as p
    project_path = DEST / f'{STEM}.kicad_pro'
    project_bytes = project_path.read_bytes()
    board = p.BOARD()
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
    title = board.GetTitleBlock()
    title.SetTitle('Goodjohn CPC464 USB keyboard carrier')
    title.SetRevision('1.0-prototype')
    title.SetDate('2026-10-06')
    title.SetCompany('salvogendut / Goodjohn')
    # Use Eeschema's actual net names, including explicit unconnected-pin nets.
    # This preserves Update PCB from Schematic / parity checks for unused pins.
    netlist = ET.parse(DEST / 'checks/netlist.xml').getroot()
    pad_nets = {}
    nets = {}
    for node in netlist.findall('./nets/net'):
        name = node.attrib['name']
        net = p.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
        for pin in node.findall('node'):
            pad_nets[(pin.attrib['ref'], pin.attrib['pin'])] = name
    point = lambda x, y: p.VECTOR2I(p.FromMM(x), p.FromMM(y))
    for ref, name in FOOTPRINTS.items():
        fp = p.FootprintLoad(str(DEST / 'libraries/Goodjohn.pretty'), name)
        if fp is None:
            raise RuntimeError(name)
        fp.SetFPID(p.LIB_ID(LIB, name))
        fp.SetReference(ref)
        fp.SetValue(VALUES[ref])
        fp.SetPath(p.KIID_PATH('/' + uid('root') + '/' + uid(ref)))
        board.Add(fp)
        x, y, angle = PCB_POS[ref]
        fp.SetPosition(point(x, y))
        fp.SetOrientationDegrees(angle)
        fp.Reference().SetVisible(False)  # Board silk labels below include refs.
        fp.Value().SetVisible(False)
        for pad in fp.Pads():
            net = pad_nets.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        if ref.startswith('H'):
            fp.SetAttributes(fp.GetAttributes() | p.FP_EXCLUDE_FROM_POS_FILES)
    x0, y0, x1, y1 = OUTLINE
    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                 ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        edge = p.PCB_SHAPE()
        edge.SetShape(p.SHAPE_T_SEGMENT)
        edge.SetStart(point(*a)); edge.SetEnd(point(*b))
        edge.SetLayer(p.Edge_Cuts); edge.SetWidth(p.FromMM(0.05))
        board.Add(edge)
    def label(text, x, y, size=1, angle=0, layer=p.F_SilkS):
        obj = p.PCB_TEXT(board)
        obj.SetText(text); obj.SetPosition(point(x, y))
        obj.SetTextSize(point(size, size)); obj.SetTextThickness(p.FromMM(0.15))
        obj.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T)); obj.SetLayer(layer)
        if layer == p.B_SilkS:
            obj.SetMirrored(True)
        board.Add(obj)
    for text, x, y, size, angle in [
        ('GOODJOHN', 153, 104, 2, 0), ('CPC464 USB / v1.0', 153, 107.5, 1, 0),
        ('U1  PICO', 119.05, 153.8, 1, 0), ('USB TO PC', 119, 108.5, 1, 0),
        ('1', 107.3, 103.05, 1, 0), ('40', 131, 103.05, 1, 0),
        ('20', 107.1, 151.3, 1, 0), ('21', 131, 151.3, 1, 0),
        ('J1  INLINE 19', 169.8, 132.8, 1.1, 90),
        ('19', 177, 110.16, 1, 0), ('1', 177, 155.88, 1.2, 0),
        ('J3 / B', 141.4, 111.8, 1, 0), ('J2 / A', 152, 111.8, 1, 0),
        ('1', 146.8, 115.24, 1, 0), ('1', 155.1, 115.24, 1, 0),
        ('10', 139.8, 138.1, 1, 0), ('10 NC', 156.4, 138.1, 0.9, 0),
        ('B = EVEN', 142.2, 142, 0.85, 0), ('A = ODD', 153, 142, 0.85, 0),
        ('USE J1 OR J2 + J3', 150, 148, 1.05, 0),
        ('ONE KEYBOARD ONLY', 150, 151, 1.05, 0),
        ('USB KEYBOARD ONLY', 138, 159, 1.4, 0),
        ('DISCONNECT CPC MOTHERBOARD', 138, 162.5, 1.1, 0),
    ]:
        label(text, x, y, size, angle)
    label('GOODJOHN v1.0 / PROTOTYPE\n80 x 66 mm / RP2040 Pico\nNo CPC pass-through\nDisconnect CPC even when off', 151, 153, 1.1, layer=p.B_SilkS)
    # Ground is confined to the carrier, never a keyboard connector contact.
    for layer in [p.F_Cu, p.B_Cu]:
        zone = p.ZONE(board)
        zone.SetLayer(layer); zone.SetNet(nets['/GND'])
        zone.SetLocalClearance(p.FromMM(0.3))
        zone.SetThermalReliefGap(p.FromMM(0.3))
        zone.SetThermalReliefSpokeWidth(p.FromMM(0.3))
        zone.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
        zone.SetMinThickness(p.FromMM(0.25))
        poly = zone.Outline(); poly.NewOutline()
        for x, y in [(x0+0.5,y0+0.5),(x1-0.5,y0+0.5),(x1-0.5,y1-0.5),(x0+0.5,y1-0.5)]:
            poly.Append(int(p.FromMM(x)), int(p.FromMM(y)))
        board.Add(zone)
    # Keep screw/washer envelopes clear of copper on both sides.
    for ref in ['H1', 'H2', 'H3', 'H4']:
        x, y, _ = PCB_POS[ref]
        zone = p.ZONE(board)
        zone.SetIsRuleArea(True)
        zone.SetLayerSet(p.LSET.AllCuMask(2))
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowZoneFills(True)
        zone.SetDoNotAllowPads(False)
        zone.SetZoneName(f'{ref} screw clearance')
        poly = zone.Outline(); poly.NewOutline()
        for dx, dy in [(-3.5,-3.5),(3.5,-3.5),(3.5,3.5),(-3.5,3.5)]:
            poly.Append(int(p.FromMM(x+dx)), int(p.FromMM(y+dy)))
        board.Add(zone)
    p.SaveBoard(str(DEST / f'{STEM}.kicad_pcb'), board)
    project_path.write_bytes(project_bytes)
    print('Wrote schematic-linked placement, outline, silk and ground pours.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--libraries', type=Path, help='KiCad library root containing symbols/ and footprints/')
    parser.add_argument('--schematic', action='store_true')
    parser.add_argument('--pcb', action='store_true')
    args = parser.parse_args()
    if args.libraries:
        libraries(args.libraries)
    if args.schematic:
        schematic()
    if args.pcb:
        pcb()
