#!/usr/bin/env python3
"""Exchange routing with a local Specctra-compatible router (KiCad 10 Python).

Export does not change the board. Import applies a specified session file;
always run KiCad DRC with schematic parity and zone refill after importing.
"""
import argparse
from pathlib import Path
import pcbnew as p
from design import DEST, STEM
from sexpr import loads, dumps, child

parser = argparse.ArgumentParser(description=__doc__)
mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument('--export', type=Path, metavar='DSN')
mode.add_argument('--import-session', type=Path, metavar='SES')
args = parser.parse_args()
filename = DEST / f'{STEM}.kicad_pcb'
data = loads(filename.read_text())
data[:] = [n for n in data if not (isinstance(n, list) and (
    n[0] in ['segment', 'via', 'arc'] or
    args.export and n[0] == 'zone' and child(n, 'keepout') is None))]
scratch = DEST / 'checks/routing-input.kicad_pcb'
scratch.write_text(dumps(data) + '\n')
board = p.LoadBoard(str(scratch))
if args.export:
    # Route the ground header pins explicitly as well. Treating an unfilled
    # pour as a complete plane can leave disconnected copper islands later.
    # LoadBoard alone uses API defaults, even alongside a .kicad_pro file.
    # Set these explicitly and inspect the exported DSN rule block.
    default = board.GetDesignSettings().m_NetSettings.GetDefaultNetclass()
    default.SetTrackWidth(p.FromMM(0.3))
    default.SetClearance(p.FromMM(0.3))  # 0.05mm margin over DRC minimum
    default.SetViaDiameter(p.FromMM(0.8))
    default.SetViaDrill(p.FromMM(0.4))
    board.SynchronizeNetsAndNetClasses(False)
    if not p.ExportSpecctraDSN(board, str(args.export.resolve())):
        raise RuntimeError('DSN export failed')
    print(f'Exported {args.export}')
else:
    if not p.ImportSpecctraSES(board, str(args.import_session.resolve())):
        raise RuntimeError('SES import failed')
    # Freerouting may neck down short pad exits. This prototype uses 0.30mm
    # throughout; restoring width is followed by KiCad's independent DRC.
    for track in board.GetTracks():
        if not isinstance(track, p.PCB_VIA):
            track.SetWidth(p.FromMM(0.3))
    # Ground stitch needed for the verified v1 routing's isolated pour strip.
    # Recheck/reposition it if changing the layout or regenerating routing.
    via = p.PCB_VIA(board)
    via.SetPosition(p.VECTOR2I(p.FromMM(119), p.FromMM(120)))
    via.SetWidth(p.FromMM(0.8)); via.SetDrill(p.FromMM(0.4))
    via.SetViaType(p.VIATYPE_THROUGH); via.SetLayerPair(p.F_Cu, p.B_Cu)
    via.SetNetCode(board.FindNet('/GND').GetNetCode()); board.Add(via)
    project_path = filename.with_suffix('.kicad_pro')
    project_bytes = project_path.read_bytes()
    p.SaveBoard(str(filename), board)
    project_path.write_bytes(project_bytes)
    print(f'Imported {args.import_session}; run DRC before fabrication export.')
