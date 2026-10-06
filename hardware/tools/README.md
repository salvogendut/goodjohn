# Hardware tooling

The saved KiCad files are the design authority. Normal edits do not require
regenerating the schematic or placement. Run these commands from the repository
root; keep the same KiCad major version (10) for reproducible validation.

## Refresh checked outputs

Install `scripts/requirements-docs.txt` into a Python virtual environment, then:

```sh
python hardware/tools/export.py --flatpak
```

Omit `--flatpak` for native `kicad-cli`. This performs ERC, netlist export,
DRC with schematic parity and zone refill, independent pin-map validation,
schematic PDF, assembly SVG, 3D render, Gerber/drill export, BOM/connector CSV,
assembly PDF and a checksummed manufacturing ZIP. It stops on a failing check.
Standard KiCad 3D libraries must be installed for the render.
The package step independently compares all Excellon drill coordinates and
diameters to the PCB and checks the exported outline corners and stack metadata.

`verify.py` compares the actual schematic netlist and PCB pad nets against
`src/board_config.h` and both pre-existing wiring SVGs. It also checks isolated
pins, ground, trace/via dimensions, the project's manufacturing minimums and
the ERC/DRC reports. It needs only Python's standard library. It does not claim
to simulate the keyboard or prove physical cable orientation.

## Recreate the initial design or reroute

These commands **replace schematic/placement/routing** and are intended for
reviewed regeneration, not routine editing of the finished board.

```sh
python hardware/tools/design.py --schematic
flatpak run --command=kicad-cli org.kicad.kicad sch export netlist \
  hardware/pico-carrier-v1/goodjohn-carrier.kicad_sch --format kicadxml \
  --output hardware/pico-carrier-v1/checks/netlist.xml
flatpak run --command=python3 org.kicad.kicad hardware/tools/design.py --pcb
flatpak run --command=python3 org.kicad.kicad hardware/tools/route.py \
  --export hardware/pico-carrier-v1/checks/carrier.dsn
```

The verified router was the official **Freerouting 2.5.0** JAR, running locally
under OpenJDK 25. It is not bundled. With its path substituted below:

```sh
java -Djava.awt.headless=true -jar /path/to/freerouting-2.5.0.jar \
  --gui.enabled=false --api_server.enabled=false -da \
  -de hardware/pico-carrier-v1/checks/carrier.dsn \
  -do hardware/pico-carrier-v1/checks/carrier.ses -mp 20 -mt 2
flatpak run --command=python3 org.kicad.kicad hardware/tools/route.py \
  --import-session hardware/pico-carrier-v1/checks/carrier.ses
python hardware/tools/export.py --flatpak
```

The committed DSN and SES record the routing input/result. The import helper
restores all tracks to 0.30 mm (the router can narrow short pad exits) and adds
the v1 ground stitch at (119,120) mm. If routing or placement changes, recheck
that stitch and every design rule; a new run may need different local fixes.
Export strips ordinary pours from the temporary routing copy so all ground
pins get explicit tracks; mounting rule areas remain. Pours stay in the saved
board and are filled by KiCad. `routing-input.kicad_pcb` is disposable/ignored.

KiCad's Python `LoadBoard` can use default net-class settings rather than the
adjacent project. The exchange script explicitly supplies 0.30 mm track/clearance
and 0.80/0.40 mm vias. It preserves the project file across API saves, which can
otherwise reset design constraints in this environment. Check the DSN rules,
the actual imported dimensions and the `.kicad_pro` minimums, not only a successful
tool exit. Final manufacturing minimums are 0.25 mm width/clearance.

For refreshing vendored libraries, use `design.py --libraries PATH`, where PATH
contains KiCad's `symbols/` and `footprints/` directories. Review all library
changes and preserve [the license/provenance](../pico-carrier-v1/libraries/README.md).
That command is not needed to open, edit, validate or export the delivered design.

Official references:
[KiCad CLI](https://docs.kicad.org/10.0/en/cli/cli.html),
[Freerouting CLI](https://github.com/freerouting/freerouting/blob/v2.5.0/docs/command_line_arguments.md).
