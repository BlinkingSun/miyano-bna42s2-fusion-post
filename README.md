# Miyano BNA-42S2 post for Autodesk Fusion

A Fusion post processor and machine definition for the **Citizen-Miyano BNA-42S2**: a twin-spindle turret lathe with a FANUC 0i-TD control, main spindle SP1, opposed sub-spindle SP2 on a B slide, an 8-station live turret, and C-axis on both spindles. It was written for a 2016 machine.

> **Safety.** Several machine-specific M-codes are still unverified or blank (see the checklist). Every posted program starts with a banner listing what is missing or still needs checking. Prove out every program on the machine: single block, reduced rapids, B well back from the part. No warranty; use at your own risk. Not affiliated with Citizen Machinery, Miyano, FANUC or Autodesk.

## Files

| Path | What it is |
|---|---|
| `Miyano BNA-42S2.cps` | The post. |
| `machine/Citizen-Miyano BNA-42S2.mch` | Fusion machine definition, linked to the post. |
| `examples/` | Programs posted from a test part (see "What was verified"). |
| `tools/make_miyano_post.py` | Builds the post from Autodesk's Doosan mill-turn post. |

## Install in Fusion

1. Copy `Miyano BNA-42S2.cps` into Fusion's local posts folder:
   - Windows: `%APPDATA%\Autodesk\Fusion 360 CAM\Posts\`
   - Mac: `~/Library/Application Support/Autodesk/Fusion 360 CAM/Posts/`
2. Restart Fusion. In the NC Program dialog, the post appears under your local posts as **Citizen-Miyano BNA-42S2 (FANUC 0i-TD)**.
3. Optional: import the machine in Manufacture > Manage > Machine Library > Import, choosing `machine/Citizen-Miyano BNA-42S2.mch`. Then pick it in each setup (Setup > Machine) so the NC program selects this post automatically. If Fusion shows the machine with no post, link it to the post from step 1 in the machine's settings.

## How it was built

Autodesk has no Miyano post. Their "DN Solutions (Doosan) Mill/Turn, Fanuc 0i" post covers the same layout: one turret on X/Z, a main spindle, an opposed sub-spindle on a B slide, live tools, and C on both spindles. It also already handles Fusion's Subspindle Grab, Part and Subspindle Return operations. `tools/make_miyano_post.py` forks it and replaces the machine layer:

- One machine model (BNA-42S2): no Y axis, no tilting B head, a single turret, polar interpolation on.
- Every machine-specific M-code is a post property (group **Miyano M-codes**). A blank value outputs nothing. Doosan-only functions are never output: the interlock bypass, interference check, M176/M177 tapping mode, M48/M49 override lock, and the G350 parting check.
- Sub-spindle B positions are written in machine coordinates (see below).
- During a transfer only X goes home (G28 U0). The turret's Z axis doesn't drive toward an advanced sub-spindle. This follows Miyano's own cutoff example.
- After a part-off, a Subspindle Return never opens the SP1 chuck on the bar.
- Speed limits: SP1 6,000 rpm, SP2 5,000 rpm, live tools 5,000 rpm.
- Coolant is flood only (M8/M9).
- Every program starts with a banner. It lists the codes that program needs but that are still blank (**NOT READY**), and the codes not yet confirmed (**VERIFY**).

To rebuild, download the base post from Autodesk's library, then run the script:

```sh
mkdir -p base
curl -o "base/doosan mill-turn fanuc.cps" \
  "https://cam.autodesk.com/posts/download.php?name=doosan%20mill-turn%20fanuc"
python3 tools/make_miyano_post.py "base/doosan mill-turn fanuc.cps" "Miyano BNA-42S2.cps"
```

The script was written against base revision 44243 (2026-09-18). Every edit is an exact match, so a newer upstream post that changed one of the edited spots stops the build with a message instead of producing a half-patched post. Make lasting changes in the script, not by hand in the `.cps`.

Machine facts used, all from the BNA-42S2 column of Miyano's BNA-S2/DHY3 brochure (2019):
- Control: FANUC 0i-TD
- Strokes: X1 135 mm, Z1 235 mm, B 310 mm; rapid 20 m/min on all three
- SP1 6,000 rpm with a 5" chuck; SP2 5,000 rpm with a collet
- 8 turret stations, all live, live tools to 5,000 rpm
- 64 offset pairs
- Polar and cylindrical interpolation; rigid tapping on both spindles and the live tools

## Before the first program runs

### 1. Fill in and check the M-codes

On the control, open the G/M code list, or check the M-code list in the programming manual or on the machine. Compare it with the **Miyano M-codes** properties (NC Program, then Post properties). Change the defaults in the post file itself so they stick.

| Property | Default | Source |
|---|---|---|
| SP2 chuck open / close | M117 / M118 | Miyano BNA-S brochure program example |
| Sync forward (SP1+SP2), extra word | M403, P11 | brochure |
| Wait for sync | M408 | brochure ("M403 completion confirmation") |
| Sync stop | M205 | brochure |
| Position coder SP1 | M91 | brochure |
| SP1 forward / reverse / stop | M3 / M4 / M5 | standard FANUC |
| Rigid tap, orient SP1 | M29, M19 | standard FANUC |
| SP2 forward / reverse / stop | M103 / M104 / M105 | inferred (M103 appears in a BNA-42MSY sub-spindle example; follows the M1xx = SP2 pattern) |
| SP1 chuck close / open | M18 / M17 | inferred (Miyano ANC-45S report; matches M117/M118) |
| Live tool forward / reverse / stop | blank | **not published; required for live tooling** |
| C-axis on / off, SP1 and SP2 | blank | **required for C-axis work** |
| Position coder SP2 | blank | **required for feed-per-rev turning on SP2** (likely M92, unconfirmed) |
| Sync reverse, phase sync | blank | needed only if you use them |
| Part catcher, chip conveyor, air blow, part counter, C clamp | blank | options; fill in if fitted |
| Sub-spindle home block | `G53 B0.` | unverified. Use whatever your existing programs use. |

When every code is confirmed, set **M-codes verified on the machine** to Yes in the post. That removes the VERIFY banner.

### 2. Measure the sub-spindle B offset

Fusion gives grab and return positions as work Z. The Miyano commands B in machine coordinates (the brochure uses `G0 B-260.` and `G01 B-290.43 F4000.`). The post converts them with **Sub-spindle B at work Z0** (`subBAtWorkZ0`): face a part, jog B until the SP2 collet face is at that face (work Z0), and enter the B machine coordinate. The post writes **B = offset + Z**. That assumes +B and +Z both point away from SP1; confirm it while jogging. The post won't run a transfer until this value is set.

In each Subspindle Grab, set the feed-position offset to at least 2–5 mm. Otherwise B rapids almost onto the part, and the post warns about it.

### 3. Prove out

Prove out with single block, rapid override at 25% or less, and the sub-spindle program run with B well back from the part. Check the first SP2 operation especially carefully: the Z direction and the B working position for SP2 work are the least-verified parts (see the open items).

## What was verified

The test part is a Ø38/Ø30 step with an axial Ø8 hole, an off-center Ø4 face hole and a radial Ø5 cross hole. Its operations were posted in Fusion, and the output is in `examples/`. The test seat slows rapids to the cutting feed, so some rapid moves in these files appear as G1.

- `O2002 face SP1.nc`: facing on SP1, with M91, G50/G96 and M3. Its body matches the unmodified Doosan post output; only the machine codes differ. The G50 S5000 comes from the sample tool's own rpm limit.
- `O5003 face drill live C-axis.nc`: live Ø4 on the face, G83 with C positioning and G98. The NOT READY banner is correct: the live-tool and C-axis codes are blank.
- `O5004 back face SP2.nc`: facing on SP2 with M103/M105. NOT READY until the SP2 position coder is set.
- `O5002 cutoff with SP2 pickup.nc` (test B offset −300): M117, G96 S200 M403 P11, G0 B-295., G1 B-301., M408, M118. Then G28 U0 only, part-off with T0303, B home with SP1 still clamped, and M205. That matches the order in Miyano's example.

## What was not tested

The test seat could not post programs containing tool changes, and could not generate tool-orientation operations. Check these first on a full commercial seat:

1. **A full multi-tool program.** Tool-to-tool transitions have not been seen: X/Z home, M1, the next T-code and spindle start. Post a complete job and read every tool change.
2. **Radial live tooling** (cross holes, milling on the diameter). Check the plane, C positioning and the canned cycle on the first one.

## Simulation

- **Toolpath and stock simulation:** select a setup, then Actions > Simulate. This shows stock removal for the SP1 and SP2 setups, including the part handed over by the grab and part-off.
- **The machine definition:** built from Fusion's generic 2-axis lathe template, with the spindle limited to 6,000 rpm and linked to the post. It has **no 3D model and no B/sub-spindle axis**, so it is not a collision-checking machine simulation.

## Open items

- **SP2 working position.** The post sends B home for SP2 work, as the Doosan logic does. If your BNA programs move B to a working position for back-working, that move needs adding.
- **CSS while synchronized.** Fusion's part-off defaults to constant surface speed (G96), so the post outputs `G96 ... M403 P11`. Miyano's example uses G97 rpm. Set the part-off to rpm unless the control is known to accept G96 while synchronized.
- **Sync reissued for the part-off.** The post outputs M403 again at the part-off, while the spindles are already synchronized. Confirm the control accepts that.
- **Not implemented yet:**
  - the G506 K0.05 B pull before cutoff (puts the part under tension)
  - the G591/M291 B-axis background program that overlaps B moves with turret moves
  - bar-feed codes

If you run one of these machines, an issue with a real program from it, or a photo of its M-code list, is the quickest way to close these items.

## License

- `Miyano BNA-42S2.cps` is a modified version of Autodesk's "DN Solutions (Doosan) Mill/Turn with Fanuc 0i/31i control" post from the Fusion post library. Most of its code is Autodesk's, and Autodesk's copyright notice is kept in the file header. The unmodified Autodesk post is not included in this repository; the build steps download it from Autodesk.
- Everything else (the build script, the machine definition, the examples and this README) is under the MIT License. See `LICENSE`.

Citizen, Miyano, FANUC, Autodesk and Fusion are trademarks of their respective owners.
