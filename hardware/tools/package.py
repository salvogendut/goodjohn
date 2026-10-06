#!/usr/bin/env python3
"""Write the BOM, connector CSV, assembly PDF and checksummed fabrication ZIP.

Run after verify.py and KiCad exports. Requires scripts/requirements-docs.txt.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import re
from collections import Counter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from design import DEST, STEM, GPIO, PICO_GPIO_PINS
from sexpr import loads, child, children


def verify_fabrication():
    """Check drill sizes/positions against the final PCB, including rotation."""
    board = loads((DEST/f'{STEM}.kicad_pcb').read_text())
    expected = {'PTH': [], 'NPTH': []}
    def hit(x,y,d):
        return (round(x,3),round(y,3),round(d,3))
    for fp in children(board,'footprint'):
        at=child(fp,'at'); ox,oy=map(float,at[1:3])
        a=math.radians(float(at[3]) if len(at)>3 else 0)
        for pad in children(fp,'pad'):
            drill=child(pad,'drill')
            if not drill:
                continue
            pos=child(pad,'at'); x,y=map(float,pos[1:3])
            expected['NPTH' if pad[2]=='np_thru_hole' else 'PTH'].append(
                hit(ox+x*math.cos(a)+y*math.sin(a),oy-x*math.sin(a)+y*math.cos(a),float(drill[1])))
    for v in children(board,'via'):
        expected['PTH'].append(hit(*map(float,child(v,'at')[1:3]),float(child(v,'drill')[1])))
    for kind, hits in expected.items():
        source=(DEST/f'fabrication/gerbers/{STEM}-{kind}.drl').read_text()
        if 'METRIC' not in source or 'G90' not in source:
            raise ValueError('Expected absolute metric Excellon')
        tools={}; actual=[]; tool=None; x=y=None
        for line in source.splitlines():
            m=re.fullmatch(r'T(\d+)C([\d.]+)',line)
            if m:
                tools[int(m[1])]=float(m[2]); continue
            m=re.fullmatch(r'T(\d+)',line)
            if m:
                tool=int(m[1]); continue
            if line.startswith(('X','Y')):
                mx=re.search(r'X(-?[\d.]+)',line); my=re.search(r'Y(-?[\d.]+)',line)
                if mx: x=float(mx[1])
                if my: y=-float(my[1])
                actual.append(hit(x,y,tools[tool]))
        if Counter(actual)!=Counter(hits):
            raise ValueError(f'{kind} drill locations/sizes differ from the board')
    profile=(DEST/f'fabrication/gerbers/{STEM}-Edge_Cuts.gm1').read_text()
    if '%FSLAX46Y46*%' not in profile or '%MOMM*%' not in profile:
        raise ValueError('Unexpected profile Gerber units/format')
    vertices={(int(x)/1e6,-int(y)/1e6) for x,y in re.findall(r'X(-?\d+)Y(-?\d+)D0[12]\*',profile)}
    if vertices!={(100,100),(180,100),(180,166),(100,166)}:
        raise ValueError(f'Unexpected profile vertices: {vertices}')
    job=json.loads((DEST/f'fabrication/gerbers/{STEM}-job.gbrjob').read_text())
    if job['GeneralSpecs']['LayerNumber']!=2 or job['GeneralSpecs']['BoardThickness']!=1.6:
        raise ValueError('Unexpected fabrication layer count/thickness')
    report={'result':'PASS','PTH_hits':len(expected['PTH']), 'NPTH_hits':len(expected['NPTH']),
            'drill_coordinates_and_diameters':'match final PCB', 'outline_mm':[80,66],
            'layers':2,'thickness_mm':1.6}
    (DEST/'checks/fabrication.json').write_text(json.dumps(report,indent=2)+'\n')


def table(c, rows, x, top, widths, font=9, height=19):
    t = Table(rows, colWidths=widths, rowHeights=height)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#143c48')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'),
        ('FONTSIZE',(0,0),(-1,-1),font),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#eef3f4')]),
        ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#143c48')),
    ]))
    _, h = t.wrap(sum(widths), 1000)
    t.drawOn(c,x,top-h)
    return top-h


def text(c,x,y,lines,size=10,leading=15,bold=False):
    c.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
    for line in lines:
        c.drawString(x,y,line); y-=leading
    return y


def main():
    verify_fabrication()
    nodes = {}
    for net in ET.parse(DEST/'checks/netlist.xml').findall('./nets/net'):
        for n in net.findall('node'):
            nodes[(n.attrib['ref'],n.attrib['pin'])] = net.attrib['name'].removeprefix('/')
    rows = []
    for ref, count in [('J1',19),('J2',10),('J3',10)]:
        for pin in range(1,count+1):
            net = nodes[(ref,str(pin))]
            nc = net.startswith('unconnected-')
            keyboard = 'Inline 19' if ref == 'J1' else 'Bread80 CPC464 SMT J1'
            kp = pin if ref == 'J1' else 2*pin-(ref=='J2')
            rows.append([ref,pin,'NC' if nc else net,'' if nc else f'GP{GPIO[net]}',
                         '' if nc else PICO_GPIO_PINS[GPIO[net]],keyboard,kp])
    with (DEST/'docs/connections.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n'); writer.writerow(['Carrier reference','Carrier contact','Matrix net','Pico GPIO','Pico physical pin','Keyboard connector','Keyboard contact']); writer.writerows(rows)
    bom = [
        ['PCB',1,'Goodjohn carrier v1','80 x 66 mm; 2 layers; 1.6mm FR4; 1oz copper','Unbuilt prototype'],
        ['U1',1,'Raspberry Pi Pico / Pico H','Original RP2040; male headers pointing down','USB faces upper edge'],
        ['U1 sockets',2,'Female header 1x20','2.54mm pitch; 17.78mm row spacing; nominal 8.5mm body height','Match chosen male headers; sockets fitted to carrier'],
        ['J1',1,'Male header 1x19','2.54mm pitch; vertical; 0.64mm square posts','Optional for ribbon-only build'],
        ['J2 J3',2,'Male header 1x10','2.54mm pitch; vertical; 0.64mm square posts','Optional for inline-only build'],
        ['H1-H4',4,'M3 standoff/screw sets','3.2mm NPTH; head/washer envelope <=7mm','Optional; protect underside from metalwork'],
        ['USB cable',1,'USB data cable','PC host to Pico Micro-USB','Power and data on one cable'],
        ['Keyboard harness',1,'Mating 2.54mm harness','Inline 19 OR separate A/B 10-way cables','Verify every contact; bare membrane tails need adapter'],
    ]
    with (DEST/'bom.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n'); writer.writerow(['Reference','Quantity','Item','Specification','Notes']); writer.writerows(bom)
    c=canvas.Canvas(str(DEST/'docs/assembly.pdf'),pagesize=A4)
    c.setTitle('Goodjohn Pico carrier v1 - assembly and connections')
    c.setAuthor('Goodjohn / salvogendut')
    w,h=A4
    text(c,40,h-40,['GOODJOHN / PICO CARRIER v1'],18,bold=True)
    text(c,40,h-60,['Assembly guide - 2026-10-06 - UNBUILT PROTOTYPE'],10)
    c.setFillColor(colors.HexColor('#fff0de')); c.rect(40,h-117,w-80,42,fill=1,stroke=0)
    c.setFillColor(colors.black)
    text(c,49,h-91,['USB KEYBOARD ONLY: disconnect the CPC motherboard, even when off.',
                       'Use one keyboard via J1 OR J2 + J3. No CPC pass-through.'],10,15,True)
    c.drawImage(str(DEST/'docs/carrier-3d.png'),40,326,width=w-80,height=(w-80)*0.75,preserveAspectRatio=True,anchor='c')
    text(c,40,318,['KiCad render; 80 x 66 mm board. Four 3.2 mm mounting holes.'],9)
    table(c,[['Fit to carrier','Quantity / specification'],
             ['U1 module','1 x original RP2040 Pico / Pico H'],
             ['U1 female sockets','2 x 1-by-20; 2.54mm pitch; 17.78mm row spacing'],
             ['J1 male header','1 x 1-by-19, 2.54mm; pin 1 at BOTTOM'],
             ['J2 / A and J3 / B','2 x 1-by-10, 2.54mm; pin 1 at TOP'],
             ['USB','One PC-to-Pico USB data cable supplies power']],40,300,[135,w-215],9,21)
    text(c,40,151,['Pico USB faces the top edge. Insert U1 only after checking the unpowered carrier.',
                  'Carrier headers take a mating harness, not a bare membrane tail.',
                  'Hole centres from top-left: (4,4), (76,4), (4,62), (76,62) mm.',
                  'Check actual sockets/cable fit; the carrier has not been bench-tested.'],9,15)
    text(c,40,61,['Editable project, BOM and full notes: hardware/pico-carrier-v1/README.md'],9)
    c.showPage()
    text(c,40,h-40,['CONNECTOR CHECK SHEET'],18,bold=True)
    text(c,40,h-61,['All numbers below are PHYSICAL connector contacts. GPIO is a separate column.'],9)
    matrix=[['Net','GPIO','Pico pin','J1 inline','Ribbon carrier','Bread80 J1']]
    for r in rows[:19]:
        ribbon=next(rr for rr in rows[19:] if rr[2]==r[2])
        matrix.append([r[2],r[3],r[4],r[1],f'{ribbon[0]}.{ribbon[1]}',ribbon[6]])
    y=table(c,matrix,40,h-80,[50,62,70,72,126,135],9,18)
    text(c,40,y-18,['J2.10 = A10 = Bread80 J1 pad 19: NO CONNECTION.',
                    'J3.10 = B10 = Bread80 J1 pad 20: Y1, required.',
                    'Bread80 ribbon mode: LK1 1-2, LK2 1-2; LK3 and bonus links OPEN.'],10,15,True)
    text(c,40,y-75,['Before USB: remove Pico, disconnect CPC, then continuity-check every cable path.',
                    'Different matrix nets must be isolated; none may connect to GND or power.',
                    'Attach keyboard only after those checks. Key continuity appears only when held.',
                    'Diode keyboards may need diode-test mode and the correct probe polarity.'],9,14)
    checks=[['Key','Inline carrier contacts','Pico physical pins'],
            ['1','J1.3 + J1.11','16 + 14'],['2','J1.4 + J1.11','17 + 14'],
            ['Esc','J1.5 + J1.11','19 + 14'],['Main Enter','J1.5 + J1.17','19 + 6'],
            ['Space','J1.10 + J1.14','25 + 10'],['DEL / Backspace','J1.1 + J1.2','26 + 15']]
    bottom=table(c,checks,40,y-145,[125,225,165],9,18)
    text(c,40,bottom-21,['After checks, fit Pico and use the existing Goodjohn firmware with ghost suppression.',
                         'ERC / DRC / pin-map checks passed; physical fit and keyboard tests remain pending.'],9,14)
    c.save()
    # SVG exports are transparent; give the printable assembly drawing a white
    # background so it remains legible in repository dark mode too.
    svg=DEST/'docs/assembly-top.svg'; tree=ET.parse(svg); root=tree.getroot()
    ns='{http://www.w3.org/2000/svg}'
    if root.find(f'{ns}rect[@id="paper-background"]') is None:
        box=root.attrib['viewBox'].split()
        root.insert(0,ET.Element(ns+'rect',{'id':'paper-background','x':box[0],'y':box[1],
                     'width':box[2],'height':box[3],'fill':'white'}))
        ET.register_namespace('',ns[1:-1]); tree.write(svg,encoding='utf-8',xml_declaration=True)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    archive=DEST/'fabrication/goodjohn-carrier-v1-gerbers.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted((DEST/'fabrication/gerbers').iterdir()):
            z.write(f,arcname=f.name)
    sources=[DEST/f'{STEM}.{ext}' for ext in ['kicad_sch','kicad_pcb','kicad_pro']]
    sources += [DEST/f'checks/{name}' for name in ['erc.json','drc.json','pinmap.json','fabrication.json']]
    sources += [archive]+sorted((DEST/'fabrication/gerbers').iterdir())
    manifest=''.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(DEST)}\n' for f in sources)
    (DEST/'fabrication/SHA256SUMS.txt').write_text(manifest)
    print('Wrote BOM, 39-contact CSV, two-page assembly PDF, Gerber ZIP and SHA256 manifest.')


if __name__ == '__main__':
    main()
