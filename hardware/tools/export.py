#!/usr/bin/env python3
"""Validate the saved design and refresh fabrication and review artifacts.

Use --flatpak for org.kicad.kicad; otherwise kicad-cli must be on PATH.
Run in the documentation venv (scripts/requirements-docs.txt). No network used.
"""
import argparse
import subprocess
import sys
from design import ROOT, DEST, STEM

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--flatpak',action='store_true')
args=parser.parse_args()
cli=['flatpak','run','--command=kicad-cli','org.kicad.kicad'] if args.flatpak else ['kicad-cli']
sch=str(DEST/f'{STEM}.kicad_sch'); pcb=str(DEST/f'{STEM}.kicad_pcb')


def run(arguments):
    subprocess.run(cli+arguments,check=True,cwd=ROOT)


run(['sch','erc',sch,'--output',str(DEST/'checks/erc.json'),'--format','json','--exit-code-violations'])
run(['sch','export','netlist',sch,'--format','kicadxml','--output',str(DEST/'checks/netlist.xml')])
run(['pcb','drc',pcb,'--output',str(DEST/'checks/drc.json'),'--format','json',
     '--schematic-parity','--refill-zones','--save-board','--exit-code-violations'])
subprocess.run([sys.executable,str(ROOT/'hardware/tools/verify.py')],check=True)
run(['sch','export','pdf',sch,'--output',str(DEST/'docs/schematic.pdf')])
run(['pcb','export','svg',pcb,'--output',str(DEST/'docs/assembly-top.svg'),
     '--layers','F.SilkS,F.Fab,Edge.Cuts','--mode-single','--fit-page-to-board',
     '--exclude-drawing-sheet','--sketch-pads-on-fab-layers','--black-and-white'])
run(['pcb','render',pcb,'--output',str(DEST/'docs/carrier-3d.png'),'--width','1600',
     '--height','1200','--quality','high','--background','opaque','--rotate','340,0,20','--zoom','0.82'])
run(['pcb','export','gerbers',pcb,'--output',str(DEST/'fabrication/gerbers')+'/',
     '--layers','F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts','--subtract-soldermask'])
run(['pcb','export','drill',pcb,'--output',str(DEST/'fabrication/gerbers')+'/',
     '--format','excellon','--excellon-units','mm','--excellon-separate-th',
     '--generate-report','--report-path',str(DEST/'checks/drill-report.txt')])
subprocess.run([sys.executable,str(ROOT/'hardware/tools/package.py')],check=True)
