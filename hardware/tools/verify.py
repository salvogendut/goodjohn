#!/usr/bin/env python3
"""Cross-check the actual schematic/PCB nets against firmware and wiring SVGs.

Run after exporting checks/netlist.xml with KiCad, and after ERC/DRC. Python
stdlib only. This tests external pin-map invariants, not generator wording.
"""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'hardware/pico-carrier-v1'
STEM = 'goodjohn-carrier'


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    config = (ROOT / 'src/board_config.h').read_text()
    gpio = {}
    for array, prefix, count in [('row_gpios', 'Y', 10), ('col_gpios', 'X', 9)]:
        body = re.search(rf'{array}\[[^]]*\]\s*=\s*\{{([^}}]+)\}}', config)[1]
        values = [int(n.strip()) for n in body.split(',')]
        check(len(values) == count, f'Firmware changed: {array}')
        gpio.update({f'{prefix}{i}': n for i, n in enumerate(values, 1)})
    # Physical header pin mapping from the Raspberry Pi Pico published pinout.
    pins = dict(zip(range(2, 21), [4,5,6,7,9,10,11,12,14,15,16,17,19,20,21,22,24,25,26]))
    expected = {}
    for e in ET.parse(ROOT / 'docs/wiring.svg').iter():
        a = e.attrib
        if 'data-contact' in a and 'data-net' in a:
            net = a['data-net']
            check(int(a['data-gpio']) == gpio[net], f'Stale inline SVG: {net}')
            check(int(a['data-pico-pin']) == pins[gpio[net]], f'Pico pin mismatch: {net}')
            expected.setdefault('/'+net, set()).update({('J1', a['data-contact']), ('U1', str(pins[gpio[net]]))})
    check(len(expected) == 19, 'Expected 19 inline matrix signals')
    for e in ET.parse(ROOT / 'docs/wiring-dual-ribbon.svg').iter():
        a = e.attrib
        if 'data-ribbon' in a and 'data-net' in a:
            net = a['data-net']
            if net not in gpio:
                continue
            check(int(a['data-gpio']) == gpio[net], f'Stale two-ribbon SVG: {net}')
            ref = {'A': 'J2', 'B': 'J3'}[a['data-ribbon']]
            expected['/'+net].add((ref, a['data-position']))
    check(all(len(nodes) == 3 for nodes in expected.values()), 'Each signal needs exactly three pads')
    expected['/GND'] = {('U1', str(n)) for n in [3,8,13,18,23,28,38]}

    schematic = {}
    for net in ET.parse(DEST / 'checks/netlist.xml').findall('./nets/net'):
        name = net.attrib['name']
        schematic[name] = {(n.attrib['ref'], n.attrib['pin']) for n in net.findall('node')}
    board = loads((DEST / f'{STEM}.kicad_pcb').read_text())
    actual = {}
    for fp in children(board, 'footprint'):
        ref = next(p[2] for p in children(fp, 'property') if p[1] == 'Reference')
        for pad in children(fp, 'pad'):
            net = child(pad, 'net')
            if net:
                actual.setdefault(net[-1], set()).add((ref, pad[1]))
    check(actual == schematic, 'PCB and exported schematic pin nets differ')
    for net, nodes in expected.items():
        check(actual.get(net) == nodes, f'Pin mapping mismatch on {net}: {actual.get(net)} != {nodes}')
    for name, nodes in actual.items():
        if name not in expected:
            check(name.startswith('unconnected-') and len(nodes) == 1,
                  f'Unexpected connection {name}: {nodes}')
    check(any(nodes == {('J2','10')} and name.startswith('unconnected-') for name,nodes in actual.items()),
          'Ribbon A10 must be isolated')
    check(('J3','10') in actual['/Y1'], 'Ribbon B10 must carry Y1')
    check({('J1','5'),('U1','19'),('J2','4')} == actual['/X3'], 'Esc column changed')
    check({('J1','11'),('U1','14'),('J3','2')} == actual['/Y9'], 'Esc row changed')
    for node in children(board, 'segment'):
        check(float(child(node,'width')[1]) >= 0.25, 'Trace below minimum width')
    for node in children(board, 'via'):
        check(float(child(node,'size')[1]) >= 0.8 and float(child(node,'drill')[1]) >= 0.4,
              'Via below prototype dimensions')
    check(len(children(board, 'via')) > 0, 'Board has no routing vias')
    project = json.loads((DEST / f'{STEM}.kicad_pro').read_text())
    rules = project['board']['design_settings']['rules']
    check(rules['min_track_width'] >= 0.25 and rules['min_clearance'] >= 0.25,
          'Project manufacturing rules changed or were reset')
    check(not project['board']['design_settings'].get('drc_exclusions'), 'DRC exclusions present')
    drc = json.loads((DEST/'checks/drc.json').read_text())
    for category in ['violations', 'unconnected_items', 'schematic_parity']:
        check(not drc[category], f'DRC {category} not clear')
    erc = json.loads((DEST/'checks/erc.json').read_text())
    check(all(not s['violations'] for s in erc['sheets']), 'ERC violations remain')
    files = [DEST/f'{STEM}.{ext}' for ext in ['kicad_sch','kicad_pcb','kicad_pro']]
    report = {
        'result': 'PASS', 'matrix_nets': 19, 'matrix_pads_checked': 57,
        'ground_pads_checked': 7, 'ribbon_A10': 'isolated', 'ribbon_B10': 'Y1',
        'erc_violations': 0, 'drc_violations': 0, 'unconnected_items': 0,
        'schematic_parity_issues': 0, 'vias': len(children(board,'via')),
        'sources': ['src/board_config.h', 'docs/wiring.svg', 'docs/wiring-dual-ribbon.svg'],
        'sha256': {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        'hardware_status': 'Unbuilt prototype; bench validation pending',
    }
    (DEST/'checks/pinmap.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS: 19 signals / 57 matrix pads, ground, isolated pins, firmware, both SVGs, ERC and DRC.')


if __name__ == '__main__':
    main()
