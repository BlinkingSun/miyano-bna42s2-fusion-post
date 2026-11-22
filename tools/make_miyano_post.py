#!/usr/bin/env python3
"""Fork Autodesk's 'doosan mill-turn fanuc.cps' into a Citizen-Miyano BNA-42S2 post.

Every edit is an exact-match replacement with an expected count, so a change in the
upstream post makes this script fail loudly instead of producing a half-patched post.

usage: make_miyano_post.py <base doosan .cps> <output .cps>

Get the base from Autodesk's post library (it is not redistributed here):
  curl -o "base/doosan mill-turn fanuc.cps" \
    "https://cam.autodesk.com/posts/download.php?name=doosan%20mill-turn%20fanuc"
Built and tested against base revision 44243 (2026-09-18).
"""
import re
import sys

if len(sys.argv) != 3:
    sys.exit(__doc__)
src_path, out_path = sys.argv[1], sys.argv[2]
s = open(src_path, encoding="utf-8").read().replace("\r\n", "\n")

BASE_REVISION = "44243"
FORKID = "81F24FEF-21F5-4964-8B51-192F39E4E385"  # fixed so rebuilds are identical
if f"$Revision: {BASE_REVISION} " not in s:
    found = re.search(r"\$Revision: (\d+)", s)
    print(f"warning: base is revision {found.group(1) if found else '?'}, tested with {BASE_REVISION}; "
          "every edit below must still match exactly or the build stops.", file=sys.stderr)


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit(f"expected {count} x {old[:70]!r}, found {n}")
    s = s.replace(old, new)


def rewrap_calls(prefix, make):
    """Rewrite `prefix(getCode(ARGS))` -> make(ARGS) with balanced-paren matching."""
    global s
    out, i, hits = [], 0, 0
    while True:
        j = s.find(prefix, i)
        if j < 0:
            out.append(s[i:])
            break
        k = j + len(prefix)  # just past 'getCode('
        depth, m = 1, k
        while depth:
            c = s[m]
            depth += (c == "(") - (c == ")")
            m += 1
        args = s[k:m - 1]          # inside getCode( ... )
        if s[m] != ")":
            sys.exit(f"unexpected text after getCode() at {j}: {s[m:m+20]!r}")
        out.append(s[i:j] + make(args))
        i = m + 1                  # skip the outer ')'
        hits += 1
    s = "".join(out)
    return hits


# ---------------------------------------------------------------- header
sub("""  Doosan Lathe post processor configuration.

  $Revision: 44243 4b725800e4ea8d6a7f366d4700627a04b820848c $
  $Date: 2026-09-18 13:14:48 $

  FORKID {C7A4BD6C-CF7A-4299-BF94-3C18351E8FA7}
*/""", f"""  Citizen-Miyano BNA-42S2 (FANUC 0i-TD) mill-turn post processor.

  Forked 2026-11-22 from Autodesk "DN Solutions (Doosan) Mill/Turn with Fanuc 0i/31i control"
  (doosan mill-turn fanuc.cps, $Revision: 44243 $, $Date: 2026-09-18 $), which has the same
  layout as the BNA-42S2: one turret (X1/Z1), main spindle SP1, opposed sub-spindle SP2 on a
  B axis, live tools, and C on both spindles.

  Machine facts used here (Miyano brochure "BNAS2/DHY3 2019", BNA-42S2 column):
    FANUC 0i-TD, X1 135 mm / Z1 235 mm / B 310 mm, rapid 20 m/min on all three
    SP1 6,000 rpm (5" chuck), SP2 5,000 rpm (collet), 8-station turret, all 8 live, 5,000 rpm
    64 offset pairs, polar + cylindrical interpolation, rigid tap on SP1, SP2 and live tools
  Codes taken from the brochure's BNA-S program example:
    M117/M118 SP2 chuck open/close, M403 P11 SP1+SP2 synchronous forward,
    M408 = wait for M403 to finish, M205 synchronous stop, M91 SP1 position-coder select.
  Every other machine-specific code is a post property (group "Miyano M-codes"). A blank
  value means "do not output". Check each one against the code list on the control before you
  run the first program; the header of each posted program lists codes that are still unset.

  FORKID {{{FORKID}}}
*/""")

sub('description = "DN Solutions (Doosan) Mill/Turn with Fanuc 0i/31i control";\nvendor = "DN Solutions (Doosan)";\nvendorUrl = "https://www.dn-solutions.com";',
    'description = "Citizen-Miyano BNA-42S2 (FANUC 0i-TD)";\nvendor = "Citizen-Miyano";\nvendorUrl = "https://www.citizen-miyano.co.jp";')
sub('longDescription = "DN Solutions (Doosan) lathe (Fanuc 0i and 31i control) post with support for mill-turn for use with Lynx and Puma.";',
    'longDescription = "Citizen-Miyano BNA-42S2 twin-spindle turret lathe, FANUC 0i-TD. Main spindle, opposed sub-spindle on B, 8-station live turret, C-axis on both spindles, cutoff pickup with M403 sync. Machine-specific M-codes are post properties; verify them on the control before first run.";')

# ---------------------------------------------------------------- machine model
sub("""    values     : [
      {title:"Puma", id:"PUMA"},
      {title:"Lynx", id:"LYNX"},
      {title:"Lynx with Y-axis", id:"LYNX_YAXIS"},
      {title:"Puma MX", id:"PUMA_MX"},
      {title:"Puma SMX", id:"PUMA_SMX"}
    ],
    value: "PUMA",""", """    values     : [
      {title:"Miyano BNA-42S2", id:"BNA42S2"}
    ],
    value: "BNA42S2",""")

# defineMachine: replace the whole model if/else chain with the BNA-42S2 configuration
start = s.index('  if (getProperty("machineModel") == "PUMA") {\n    modelType = "Puma";')
end = s.index("  // define B-axis\n", start)
s = s[:start] + """  if (getProperty("machineModel") == "BNA42S2") {
    modelType = "Miyano BNA-42S2";
    turret1GotYAxis = false; // no Y on the S2 (Y is the DHY/MSY models)
    yAxisMinimum = toPreciseUnit(0, MM);
    yAxisMaximum = toPreciseUnit(0, MM);
    xAxisMinimum = getProperty("xAxisMinimum"); // radius value
    gotBAxis = false; // B on this machine is the sub-spindle slide, not a tilting head
    bAxisIsManual = true;
    gotPolarInterpolation = true; // brochure: polar coordinate interpolation standard
    gotDoorControl = false;
    useCAxisSelectWithTurning = false;
    setProperty("useG400", false);
    useMultiAxisFeatures = false;
    useExtendedOffsets = getProperty("useExtendedOffsets") == "default" ? "false" : getProperty("useExtendedOffsets");
  } else {
    error(localize("Machine type must be 'Miyano BNA-42S2'."));
  }

""" + s[end:]

# ---------------------------------------------------------------- property defaults
def set_default(prop, old_val, new_val):
    global s
    pat = re.compile(r"(\n  " + re.escape(prop) + r": \{.*?\n    value *: *)" + re.escape(old_val) + r"(,)", re.S)
    s, n = pat.subn(lambda m: m.group(1) + new_val + m.group(2), s, count=1)
    if n != 1:
        sys.exit(f"default for {prop} not found ({old_val})")

set_default("usePartCatcher", "true", "false")       # option on the S2; enable if fitted
set_default("gotChipConveyor", "true", "false")      # option; code below is a property
set_default("maxTool", "24", "8")                    # 8-station turret
set_default("useG53ForXfer", '"g53"', '"linear"')    # brochure: G01 B-290.43 F4000.
set_default("transferType", '"phase"', '"speed"')    # M403 = speed sync; phase code unknown
set_default("cutoffConfirmation", '"true"', '"false"')  # G350/G133 are Doosan-only

# P-code spindle selection is a Doosan feature; Miyano uses separate codes per spindle
sub("""  useSpindlePcodes: {
    title      : "Use P-codes for spindle selection",
    description: "Enable if P11, P12, etc. are used for spindle selection.  Disable if unique M-codes are used for spindle selection.",
    group      : "preferences",
    type       : "boolean",
    value      : true,
    scope      : "post"
  },
""", "")
sub("""  if (!getProperty("useSpindlePcodes")) {
    spOutput.disable();
  }
""", """  spOutput.disable(); // Miyano: separate M-codes per spindle, no P11/P12 selection words
""")

# Miyano M-code properties (inserted right after machineModel)
M = [
    # id, title, default, status, description
    ("mSP1CW", "SP1 forward", "3", "FANUC", "Main spindle forward (CW)."),
    ("mSP1CCW", "SP1 reverse", "4", "FANUC", "Main spindle reverse (CCW)."),
    ("mSP1Stop", "SP1 stop", "5", "FANUC", "Main spindle stop."),
    ("mSP2CW", "SP2 forward", "103", "inferred", "Sub-spindle forward. M103 appears in a BNA-42MSY sub-spindle tapping example."),
    ("mSP2CCW", "SP2 reverse", "104", "inferred", "Sub-spindle reverse. Inferred from the M1xx = SP2 pattern."),
    ("mSP2Stop", "SP2 stop", "105", "inferred", "Sub-spindle stop. Inferred from the M1xx = SP2 pattern."),
    ("mLiveCW", "Live tool forward", "", "unknown", "Rotary (live) tool forward. Not published; read it off the control's code list."),
    ("mLiveCCW", "Live tool reverse", "", "unknown", "Rotary (live) tool reverse."),
    ("mLiveStop", "Live tool stop", "", "unknown", "Rotary (live) tool stop."),
    ("mCAxisOnSP1", "C-axis on, SP1", "", "unknown", "Switch SP1 into C-axis (Cs) position mode."),
    ("mCAxisOffSP1", "C-axis off, SP1", "", "unknown", "Return SP1 to spindle mode."),
    ("mCAxisOnSP2", "C-axis on, SP2", "", "unknown", "Switch SP2 into C-axis position mode."),
    ("mCAxisOffSP2", "C-axis off, SP2", "", "unknown", "Return SP2 to spindle mode."),
    ("mCClampSP1", "C-axis clamp, SP1", "", "unknown", "C-axis brake/clamp on SP1 (blank = never output)."),
    ("mCUnclampSP1", "C-axis unclamp, SP1", "", "unknown", "C-axis brake release on SP1."),
    ("mCClampSP2", "C-axis clamp, SP2", "", "unknown", "C-axis brake/clamp on SP2."),
    ("mCUnclampSP2", "C-axis unclamp, SP2", "", "unknown", "C-axis brake release on SP2."),
    ("mChuckCloseSP1", "SP1 chuck close", "18", "inferred", "Main chuck/collet close. M17/M18 per a Miyano ANC-45S forum report; matches the M117/M118 SP2 pattern."),
    ("mChuckOpenSP1", "SP1 chuck open", "17", "inferred", "Main chuck/collet open."),
    ("mChuckCloseSP2", "SP2 chuck close", "118", "brochure", "Sub chuck/collet close (Miyano BNA-S program example)."),
    ("mChuckOpenSP2", "SP2 chuck open", "117", "brochure", "Sub chuck/collet open (Miyano BNA-S program example)."),
    ("mSyncSpeedCW", "Sync forward (SP1+SP2)", "403", "brochure", "SP1 & SP2 synchronous forward (M403 P11 in the brochure)."),
    ("mSyncSpeedCCW", "Sync reverse (SP1+SP2)", "", "unknown", "SP1 & SP2 synchronous reverse."),
    ("mSyncPhaseCW", "Phase sync forward", "", "unknown", "Phase-matched synchronous forward (needed only for oriented transfers)."),
    ("mSyncPhaseCCW", "Phase sync reverse", "", "unknown", "Phase-matched synchronous reverse."),
    ("mSyncStop", "Sync stop", "205", "brochure", "SP1 & SP2 synchronous stop."),
    ("mSyncConfirm", "Wait for sync", "408", "brochure", "M403 completion confirmation; output before the SP2 chuck closes."),
    ("syncExtraWord", "Word after sync code", "P11", "brochure", "Extra word written after the sync code (brochure: M403 P11)."),
    ("mPosCoderSP1", "Position coder SP1", "91", "brochure", "Select SP1 position coder (feed/rev and threading follow SP1)."),
    ("mPosCoderSP2", "Position coder SP2", "", "unknown", "Select SP2 position coder; needed for feed/rev turning on SP2."),
    ("mOrientSP1", "Orient SP1", "19", "FANUC", "Main spindle orientation."),
    ("mOrientSP2", "Orient SP2", "", "unknown", "Sub-spindle orientation."),
    ("mRigidTap", "Rigid tap", "29", "FANUC", "Rigid tapping mode (FANUC M29)."),
    ("mPartCatcherOn", "Part catcher in", "", "unknown", "Part catcher / unloader advance (option)."),
    ("mPartCatcherOff", "Part catcher out", "", "unknown", "Part catcher / unloader retract."),
    ("mChipConveyorOn", "Chip conveyor on", "", "unknown", "Chip conveyor start (option)."),
    ("mChipConveyorOff", "Chip conveyor off", "", "unknown", "Chip conveyor stop."),
    ("mAirSP1On", "Air blow SP1 on", "", "unknown", "Chuck air blow SP1 on."),
    ("mAirSP1Off", "Air blow SP1 off", "", "unknown", "Chuck air blow SP1 off."),
    ("mAirSP2On", "Air blow SP2 on", "", "unknown", "Chuck air blow SP2 on."),
    ("mAirSP2Off", "Air blow SP2 off", "", "unknown", "Chuck air blow SP2 off."),
    ("mPartCounter", "Part counter", "", "unknown", "Work counter increment (blank: the control counts on M30)."),
    ("subHomeBlock", "Sub-spindle home block", "G53 B0.", "unverified", "Block written to send the sub-spindle (B) home."),
    ("subBAtWorkZ0", "Sub-spindle B at work Z0", "", "measure", "B machine coordinate (mm) when the SP2 collet face is at the SP1 work Z0. Measure it on the machine. Subspindle grab/return positions are output as B = this value + Z (assumes B and Z are positive in the same direction, away from SP1)."),
]
prop_js = []
for pid, title, default, status, desc in M:
    prop_js.append(f"""  {pid}: {{
    title      : "{title}",
    description: "{desc} Status: {status}. Blank = do not output.",
    group      : "miyanoCodes",
    type       : "string",
    value      : "{default}",
    scope      : "post"
  }},""")
prop_js.append("""  codesVerified: {
    title      : "M-codes verified on the machine",
    description: "Set to Yes once every Miyano M-code property has been checked against the control's code list. While No, each program starts with a VERIFY banner.",
    group      : "miyanoCodes",
    type       : "boolean",
    value      : false,
    scope      : "post"
  },
  maximumSpindleSpeedSub: {
    title      : "Max sub-spindle speed",
    description: "SP2 maximum rpm (BNA-42S2: 5,000).",
    group      : "configuration",
    type       : "integer",
    range      : [0, 999999999],
    value      : 5000,
    scope      : "post"
  },
  maximumLiveToolSpeed: {
    title      : "Max live tool speed",
    description: "Rotary tool maximum rpm (BNA-42S2: 5,000). Operations above it are flagged.",
    group      : "configuration",
    type       : "integer",
    range      : [0, 999999999],
    value      : 5000,
    scope      : "post"
  },""")
anchor = '    value: "BNA42S2",\n    scope: "post"\n  },\n'
sub(anchor, anchor + "\n".join(prop_js) + "\n")
set_default("maximumSpindleSpeed", "6000", "6000")  # confirms the property is where we expect

# property group for the codes
sub("groupDefinitions = {", 'groupDefinitions = {\n  miyanoCodes: {title:"Miyano M-codes", description:"Machine-specific codes. Verify on the control.", collapsed:false, order:5},', 1) if "groupDefinitions = {" in s else None

# ---------------------------------------------------------------- coolant: flood only
sub("""var coolants = [
  {id:COOLANT_FLOOD, on:8, off:9},
  {id:COOLANT_MIST, on:138, off:139},
  {id:COOLANT_THROUGH_TOOL, spindle1:{on:108, off:109}, spindle2:{on:126, off:127}, spindleLive:{on:308, off:309}},
  {id:COOLANT_AIR, spindle1:{on:14, off:15}, spindle2:{on:114, off:115}},
  {id:COOLANT_AIR_THROUGH_TOOL},
  {id:COOLANT_SUCTION, on:7, off:9},
  {id:COOLANT_FLOOD_MIST},
  {id:COOLANT_FLOOD_THROUGH_TOOL},
  {id:COOLANT_OFF, off:9}
];""", """var coolants = [
  {id:COOLANT_FLOOD, on:8, off:9}, // FANUC standard; the 145 psi pump option needs its own code
  {id:COOLANT_MIST},
  {id:COOLANT_THROUGH_TOOL},
  {id:COOLANT_AIR},
  {id:COOLANT_AIR_THROUGH_TOOL},
  {id:COOLANT_SUCTION},
  {id:COOLANT_FLOOD_MIST},
  {id:COOLANT_FLOOD_THROUGH_TOOL},
  {id:COOLANT_OFF, off:9}
];""")

sub("var airCleanChuck = true; // use air to clean off chuck at part transfer and part eject",
    "var airCleanChuck = false; // Miyano air-blow codes are properties; enable once they are set")

# ---------------------------------------------------------------- getCode -> Miyano table
gstart = s.index("/** G/M codes setup */\nfunction getCode(code, spindle) {")
gend = s.index("/**  Returns the desired tolerance for the given section in MM.*/", gstart)
s = s[:gstart] + r'''/** Miyano code properties. Blank property = no output. */
var missingCodes = {};
function codeProp(name) {
  var v = getProperty(name);
  if (v === undefined || v === null) {
    return undefined;
  }
  v = String(v).replace(/^\s*M\s*/i, "").replace(/\s+$/, "");
  if (v === "") {
    return undefined;
  }
  var n = parseFloat(v);
  if (isNaN(n) || n < 0) {
    error(subst(localize("Post property '%1' must be an M-code number or blank (found '%2')."), name, v));
    return undefined;
  }
  return n;
}

/** Same as codeProp, but records that the program needed a code that is still blank. */
function needCode(name) {
  var n = codeProp(name);
  if (n === undefined && !missingCodes[name]) {
    missingCodes[name] = true;
    var title = properties[name] ? properties[name].title : name;
    warning(subst(localize("Miyano code '%1' (post property %2) is blank but this program needs it."), title, name));
  }
  return n;
}

/** M word for a code, or "" when the code is disabled. */
function mCodeOut(code, spindle) {
  var n = getCode(code, spindle);
  return (n === undefined) ? "" : mFormat.format(n);
}

function modalCodeOut(modal, code, spindle) {
  var n = getCode(code, spindle);
  return (n === undefined) ? "" : modal.format(n);
}

/** Synchronous spindle start words, e.g. "M403 P11". */
function syncCodeOut(method, clockwise) {
  var name = (method == TRANSFER_PHASE) ? (clockwise ? "mSyncPhaseCW" : "mSyncPhaseCCW") : (clockwise ? "mSyncSpeedCW" : "mSyncSpeedCCW");
  var n = needCode(name);
  machineState.spindlesAreSynchronized = true;
  if (n === undefined) {
    error(subst(localize("Spindle synchronization needs post property '%1' (%2)."), name, properties[name].title));
    return "";
  }
  var extra = String(getProperty("syncExtraWord") || "").replace(/^\s+|\s+$/g, "");
  return mFormat.format(n) + (extra ? " " + extra : "");
}

function spindleCodeProp(spindle, sp1Name, sp2Name, liveName) {
  switch (spindle) {
  case SPINDLE_MAIN:
    return needCode(sp1Name);
  case SPINDLE_SUB:
    return needCode(sp2Name);
  case SPINDLE_LIVE:
    return needCode(liveName);
  }
  return undefined;
}

/** G/M codes setup (Miyano BNA-42S2). Returns undefined for codes this machine does not use. */
function getCode(code, spindle) {
  switch (code) {
  case "PART_CATCHER_ON":
    return needCode("mPartCatcherOn");
  case "PART_CATCHER_OFF":
    return needCode("mPartCatcherOff");
  case "TAILSTOCK_ON":
  case "TAILSTOCK_OFF":
    error(localize("The BNA-42S2 has no tailstock."));
    return undefined;
  case "TAILSTOCK_CONTROL_ON":
  case "TAILSTOCK_CONTROL_OFF":
    return undefined;
  case "ENABLE_C_AXIS":
    machineState.cAxisIsEngaged = true;
    return needCode((spindle == SPINDLE_MAIN) ? "mCAxisOnSP1" : "mCAxisOnSP2");
  case "DISABLE_C_AXIS":
    machineState.cAxisIsEngaged = false;
    return needCode((spindle == SPINDLE_MAIN) ? "mCAxisOffSP1" : "mCAxisOffSP2");
  case "POLAR_INTERPOLATION_ON":
    return 12.1;
  case "POLAR_INTERPOLATION_OFF":
    return 13.1;
  case "STOP_SPINDLE":
    return spindleCodeProp(spindle, "mSP1Stop", "mSP2Stop", "mLiveStop");
  case "ORIENT_SPINDLE":
    return needCode((spindle == SPINDLE_MAIN) ? "mOrientSP1" : "mOrientSP2");
  case "START_SPINDLE_CW":
    if (spindle == SPINDLE_SUB && getProperty("reverseSpindle")) {
      return needCode("mSP2CCW");
    }
    return spindleCodeProp(spindle, "mSP1CW", "mSP2CW", "mLiveCW");
  case "START_SPINDLE_CCW":
    if (spindle == SPINDLE_SUB && getProperty("reverseSpindle")) {
      return needCode("mSP2CW");
    }
    return spindleCodeProp(spindle, "mSP1CCW", "mSP2CCW", "mLiveCCW");
  case "FEED_MODE_UNIT_REV":
    machineState.feedPerRevolution = true;
    return 99;
  case "FEED_MODE_UNIT_MIN":
    machineState.feedPerRevolution = false;
    return 98;
  case "CONSTANT_SURFACE_SPEED_ON":
    return 96;
  case "CONSTANT_SURFACE_SPEED_OFF":
    return 97;
  case "AUTO_AIR_ON":
    return codeProp("mAirSP1On");
  case "AUTO_AIR_OFF":
    return codeProp("mAirSP1Off");
  case "LOCK_MULTI_AXIS":
    return codeProp((spindle == SPINDLE_MAIN) ? "mCClampSP1" : "mCClampSP2");
  case "UNLOCK_MULTI_AXIS":
    return codeProp((spindle == SPINDLE_MAIN) ? "mCUnclampSP1" : "mCUnclampSP2");
  case "CLAMP_CHUCK":
    return needCode((spindle == SPINDLE_MAIN) ? "mChuckCloseSP1" : "mChuckCloseSP2");
  case "UNCLAMP_CHUCK":
    return needCode((spindle == SPINDLE_MAIN) ? "mChuckOpenSP1" : "mChuckOpenSP2");
  case "SPINDLE_SYNCHRONIZATION_PHASE":
    machineState.spindlesAreSynchronized = true;
    return codeProp("mSyncPhaseCW");
  case "SPINDLE_SYNCHRONIZATION_SPEED":
    machineState.spindlesAreSynchronized = true;
    return codeProp("mSyncSpeedCW");
  case "SPINDLE_SYNCHRONIZATION_OFF":
    machineState.spindlesAreSynchronized = false;
    forceSpindleSpeed = true;
    return needCode("mSyncStop");
  case "SPINDLE_SYNC_CONFIRM":
    return codeProp("mSyncConfirm");
  case "POSITION_CODER":
    return needCode((spindle == SPINDLE_SUB) ? "mPosCoderSP2" : "mPosCoderSP1");
  case "CONNECT_C_AXES":
    machineState.cAxesAreSynchronized = true;
    error(localize("C1/C2 axis connection is not configured for the BNA-42S2."));
    return undefined;
  case "DISCONNECT_C_AXES":
    machineState.cAxesAreSynchronized = false;
    return undefined;
  case "TORQUE_SKIP_ON":
  case "TORQUE_SKIP_OFF":
    error(localize("Torque-skip transfer is not configured for the BNA-42S2. Disable 'Stock-transfer torque control'."));
    return undefined;
  case "SELECT_SPINDLE": // state bookkeeping only; P-word output is disabled for Miyano
    switch (spindle) {
    case SPINDLE_MAIN:
      machineState.mainSpindleIsActive = true;
      machineState.subSpindleIsActive = false;
      machineState.liveToolIsActive = false;
      return 11;
    case SPINDLE_LIVE:
      machineState.mainSpindleIsActive = false;
      machineState.subSpindleIsActive = false;
      machineState.liveToolIsActive = true;
      return 12;
    case SPINDLE_SUB:
      machineState.mainSpindleIsActive = false;
      machineState.subSpindleIsActive = true;
      machineState.liveToolIsActive = false;
      return 13;
    }
    break;
  case "RIGID_TAPPING":
    return needCode("mRigidTap");
  case "INTERLOCK_BYPASS":       // Doosan-only functions: never output on the Miyano
  case "INTERFERENCE_CHECK_OFF":
  case "INTERFERENCE_CHECK_ON":
  case "YAXIS_INTERLOCK_RELEASE_ON":
  case "YAXIS_INTERLOCK_RELEASE_OFF":
    return undefined;
  case "CYCLE_PART_EJECTOR":
    return needCode("mPartCatcherOn");
  case "AIR_BLAST_ON":
    return codeProp((spindle == SPINDLE_MAIN) ? "mAirSP1On" : "mAirSP2On");
  case "AIR_BLAST_OFF":
    return codeProp((spindle == SPINDLE_MAIN) ? "mAirSP1Off" : "mAirSP2Off");
  default:
    error(localize("Command " + code + " is not defined."));
    return undefined;
  }
  return undefined;
}

/** Spindle speed limit for the spindle that holds the part in the current section. */
function partSpindleMaxRPM() {
  if (typeof currentSection != "undefined" && currentSection && currentSection.spindle == SPINDLE_SECONDARY) {
    return getProperty("maximumSpindleSpeedSub");
  }
  return getProperty("maximumSpindleSpeed");
}

var positionCoderSpindle;
/** M91-style position coder selection, written once per change of part spindle. */
function selectPositionCoder(_spindle) {
  if (_spindle == SPINDLE_LIVE || _spindle == positionCoderSpindle) {
    return;
  }
  var word = mCodeOut("POSITION_CODER", _spindle);
  if (word) {
    writeBlock(word, formatComment(_spindle == SPINDLE_SUB ? "SP2 POSITION CODER" : "SP1 POSITION CODER"));
  }
  positionCoderSpindle = _spindle;
}

''' + s[gend:]

# ---------------------------------------------------------------- call-site rewrites
n1 = rewrap_calls("mFormat.format(getCode(", lambda a: f"mCodeOut({a})")
modal_hits = 0
for modal in ("cAxisBrakeModal", "mInterferModal", "cAxisEngageModal", "tailStockModal"):
    modal_hits += rewrap_calls(f"{modal}.format(getCode(", lambda a, m=modal: f"modalCodeOut({m}, {a})")
if n1 < 30 or modal_hits < 30:
    sys.exit(f"call-site rewrite counts look wrong: mFormat={n1} modal={modal_hits}")

# getCode results used as raw numbers for the synchronized start
sub("""    var code = getCode(method == TRANSFER_PHASE ? "SPINDLE_SYNCHRONIZATION_PHASE" : "SPINDLE_SYNCHRONIZATION_SPEED", getSpindle(PART));
    spindleDir = mFormat.format(tool.clockwise ? code : (code + 1));""",
    """    spindleDir = syncCodeOut(method, tool.clockwise);""")
sub("""          mFormat.format(transferCodes.direction),""",
    """          syncCodeOut(transferType, transferCodes.spindleDirection),""")
sub("""      if (!tool.clockwise) {
        transferCodes.direction += 1;
      }
""", "")

sub("""    spindleDir = mFormat.format(tool.clockwise ? getCode("START_SPINDLE_CW", getSpindle(TOOL)) : getCode("START_SPINDLE_CCW", getSpindle(TOOL)));""",
    """    var dirCode = tool.clockwise ? getCode("START_SPINDLE_CW", getSpindle(TOOL)) : getCode("START_SPINDLE_CCW", getSpindle(TOOL));
    spindleDir = (dirCode === undefined) ? "" : mFormat.format(dirCode);""")

# Doosan-only hard-coded M-codes
sub("  mTappingModal.format(177); // reverse tapping off\n", "")
sub("writeBlock(mTappingModal.format(176));", "// Doosan M176 reverse-tapping mode removed", 2)
sub("writeBlock(gCycleModal.format(80), mTappingModal.format(177));", "writeBlock(gCycleModal.format(80));")
sub("writeBlock(mFormat.format(48)); // lock feedrate overrides", "// Doosan M48 override lock removed")
sub("writeBlock(mFormat.format(49)); // unlock feedrate overrides", "// Doosan M49 override unlock removed")
sub("""  case COMMAND_START_CHIP_TRANSPORT:
    writeBlock(mFormat.format(24));""", """  case COMMAND_START_CHIP_TRANSPORT:
    if (codeProp("mChipConveyorOn") !== undefined) {
      writeBlock(mFormat.format(codeProp("mChipConveyorOn")));
    }""")
sub("""  case COMMAND_STOP_CHIP_TRANSPORT:
    writeBlock(mFormat.format(25));""", """  case COMMAND_STOP_CHIP_TRANSPORT:
    if (codeProp("mChipConveyorOff") !== undefined) {
      writeBlock(mFormat.format(codeProp("mChipConveyorOff")));
    }""")
sub("""    writeBlock(mFormat.format(54), formatComment(localize("Increment part counter"))); //increment part counter""",
    """    if (codeProp("mPartCounter") !== undefined) {
      writeBlock(mFormat.format(codeProp("mPartCounter")), formatComment(localize("Increment part counter")));
    }""")
sub(', formatComment("INTERLOCK BYPASS")', "", s.count(', formatComment("INTERLOCK BYPASS")'))

# Sub-spindle home: the block is a property (default G53 B0.)
sub("""      writeBlock(
        gMotionModal.format(0),
        gFormat.format(28),
        gFormat.format(53),
        subOutput.format(0),
        conditional(_comment, formatComment(_comment))
      );""", """      gMotionModal.reset();
      writeBlock(
        String(getProperty("subHomeBlock")),
        conditional(_comment, formatComment(_comment))
      );""")

# Sub-spindle positions from Fusion are work Z values; the Miyano commands B in machine
# coordinates (brochure: G0 B-260. / G01 B-290.43 F4000.). Convert with the measured offset.
sub("""/** Positions the sub spindle */
function moveSubSpindle(_method, _position, _feed, _useMachineFrame, _comment, _error) {
  if (!gotSecondarySpindle) {
    return;
  }""", """/** Work Z of the SP2 collet face -> B machine coordinate (property subBAtWorkZ0). */
function subSpindleB(z) {
  var v = String(getProperty("subBAtWorkZ0") || "").replace(/^\\s+|\\s+$/g, "");
  if (v === "" || isNaN(parseFloat(v))) {
    error(localize("Set post property 'Sub-spindle B at work Z0' (subBAtWorkZ0): the B machine coordinate when the SP2 collet face is at the SP1 work Z0. Measure it on the machine."));
    return z;
  }
  return toPreciseUnit(parseFloat(v), MM) + z;
}

/** Positions the sub spindle */
function moveSubSpindle(_method, _position, _feed, _useMachineFrame, _comment, _error) {
  if (!gotSecondarySpindle) {
    return;
  }
  if (_method != HOME && !_useMachineFrame) {
    _position = subSpindleB(_position);
  }""")

# Feed position must leave clearance in front of the part before the B feed starts
sub("""      gMotionModal.reset();
      moveSubSpindle(RAPID, cycle.feedPosition, 0, cycle.useMachineFrame, "", true);""",
    """      gMotionModal.reset();
      if ((cycle.feedPosition - cycle.chuckPosition) < toPreciseUnit(2, MM)) {
        warning(subst(localize("Subspindle grab \\"%1\\": the feed position is less than 2 mm in front of the chuck position, so the sub-spindle rapids almost onto the part. Raise the feed position offset."), getOperationComment()));
      }
      moveSubSpindle(RAPID, cycle.feedPosition, 0, cycle.useMachineFrame, "", true);""")

# While a transfer is active the sub-spindle is advanced toward SP1: retract X only
# (brochure cutoff example homes U only: N8 ... G28U0; T0808M117; ...)
sub("""function goHome() {
  writeBlock(gMotionModal.format(0), gFormat.format(28), "U" + xFormat.format(0), conditional(gotYAxis, "V" + yFormat.format(0)));
  if (!machineState.isPrepositioned) {""", """function goHome() {
  writeBlock(gMotionModal.format(0), gFormat.format(28), "U" + xFormat.format(0), conditional(gotYAxis, "V" + yFormat.format(0)));
  if (machineState.stockTransferIsActive) {
    retracted = true; // sub-spindle is advanced: do not drive the turret Z home toward it
    return;
  }
  if (!machineState.isPrepositioned) {""")

# After a part-off the bar stays in SP1: never open the main chuck when the sub returns
sub("""  partCutoff = false;
  forceAny();
}""", """  if (partCutoff) {
    partWasCutOff = true;
  }
  partCutoff = false;
  forceAny();
}""")
sub("var partCutoff = false;", "var partCutoff = false;\nvar partWasCutOff = false; // a part-off ran since the last subspindle grab")
sub("""    case "secondary-spindle-grab":
      onCommand(COMMAND_COOLANT_OFF);""", """    case "secondary-spindle-grab":
      partWasCutOff = false;
      onCommand(COMMAND_COOLANT_OFF);""")
sub("""        } else if (pullMethod.unclampMode == "unclamp-primary") {
          clampChuck(getSpindle(PART), UNCLAMP);
          onDwell(cycle.dwell);
        }""", """        } else if (pullMethod.unclampMode == "unclamp-primary") {
          if (partWasCutOff) {
            warning(localize("Subspindle return after part-off: SP1 stays clamped on the bar (the return was set to unclamp the main spindle)."));
          } else {
            clampChuck(getSpindle(PART), UNCLAMP);
            onDwell(cycle.dwell);
          }
        }""")

# Wait for M403 to finish before closing the SP2 chuck on the part (brochure: M408 then M118)
sub("""        moveSubSpindle(FEED, cycle.chuckPosition, cycle.feedrate, cycle.useMachineFrame, "", true);
      }
      clampChuck(getSecondarySpindle(), CLAMP);""", """        moveSubSpindle(FEED, cycle.chuckPosition, cycle.feedrate, cycle.useMachineFrame, "", true);
      }
      if (!cycle.stopSpindle) {
        var confirmWord = mCodeOut("SPINDLE_SYNC_CONFIRM", SPINDLE_MAIN);
        if (confirmWord) {
          writeBlock(confirmWord, formatComment("WAIT FOR SYNC"));
        }
      }
      clampChuck(getSecondarySpindle(), CLAMP);""")

# ---------------------------------------------------------------- speed limits per spindle
sub('var maximumSpindleSpeed = (tool.maximumSpindleSpeed > 0) ? Math.min(tool.maximumSpindleSpeed, getProperty("maximumSpindleSpeed")) : getProperty("maximumSpindleSpeed");',
    'var maximumSpindleSpeed = (tool.maximumSpindleSpeed > 0) ? Math.min(tool.maximumSpindleSpeed, partSpindleMaxRPM()) : partSpindleMaxRPM();', 2)
sub("""      if (spindleSpeed > getProperty("maximumSpindleSpeed")) {""", """      if (spindleSpeed > partSpindleMaxRPM()) {""")
sub("""      if (spindleSpeed > 6000) {""", """      if (spindleSpeed > getProperty("maximumLiveToolSpeed")) {""")

# position coder: before every spindle start that is not a live tool
sub("""  writeBlock(
    gSpindleModeModal.format(spindleMode),
    sOutput.format(_spindleSpeed),
    spindleDir,
    spOutput.format(getCode("SELECT_SPINDLE", getSpindle(TOOL)))
  );""", """  if (!tappingMode) {
    selectPositionCoder(getSpindle(TOOL));
  }
  writeBlock(
    gSpindleModeModal.format(spindleMode),
    sOutput.format(_spindleSpeed),
    spindleDir,
    spOutput.format(getCode("SELECT_SPINDLE", getSpindle(TOOL)))
  );""")

# ---------------------------------------------------------------- program header banner
sub("""  // dump machine configuration
  var vendor = machineConfiguration.getVendor();""", """  writeMiyanoBanner();

  // dump machine configuration
  var vendor = machineConfiguration.getVendor();""")

banner = r'''
/** Lists the Miyano codes this program will need that are still blank or unverified. */
function writeMiyanoBanner() {
  var usesLive1 = false; // live tool on SP1 work
  var usesLive2 = false; // live tool on SP2 work
  var usesSubWork = false;
  var usesTransfer = false;
  for (var i = 0; i < getNumberOfSections(); ++i) {
    var section = getSection(i);
    var strategy = String(section.hasParameter("operation-strategy") ? section.getParameter("operation-strategy") : "");
    if (strategy.indexOf("SecondarySpindle") >= 0) {
      usesTransfer = true; // grab / return / pull have no cutting tool
      continue;
    }
    var t = section.getTool();
    var live = t && (t.isLiveTool() || section.getType() == TYPE_MILLING);
    if (section.spindle == SPINDLE_SECONDARY) {
      usesSubWork = true;
      usesLive2 = usesLive2 || live;
    } else {
      usesLive1 = usesLive1 || live;
    }
  }
  var need = ["mSP1CW", "mSP1Stop", "mChuckCloseSP1", "mChuckOpenSP1", "mPosCoderSP1"];
  if (usesLive1 || usesLive2) {
    need = need.concat(["mLiveCW", "mLiveStop"]);
  }
  if (usesLive1) {
    need = need.concat(["mCAxisOnSP1", "mCAxisOffSP1"]);
  }
  if (usesSubWork) {
    need = need.concat(["mSP2CW", "mSP2Stop", "mPosCoderSP2", "subHomeBlock"]);
  }
  if (usesLive2) {
    need = need.concat(["mCAxisOnSP2", "mCAxisOffSP2"]);
  }
  if (usesTransfer) {
    need = need.concat(["mChuckCloseSP2", "mChuckOpenSP2", "mSyncSpeedCW", "mSyncStop", "mSyncConfirm", "subHomeBlock", "subBAtWorkZ0"]);
  }
  var seen = {};
  var blank = [];
  var unverified = [];
  for (var j = 0; j < need.length; ++j) {
    if (seen[need[j]]) {
      continue;
    }
    seen[need[j]] = true;
    var v = String(getProperty(need[j]) || "").replace(/^\s+|\s+$/g, "");
    if (v === "") {
      blank.push(properties[need[j]].title.toUpperCase());
    } else if (!getProperty("codesVerified") && need[j] != "subBAtWorkZ0") {
      unverified.push((/^[0-9.]+$/.test(v) ? "M" : "") + v);
    }
  }
  if (blank.length > 0) {
    writeComment("NOT READY - SET THESE MIYANO CODES IN THE POST PROPERTIES");
    for (var k = 0; k < blank.length; ++k) {
      writeComment("  MISSING " + blank[k]);
    }
    warning(localize("This program needs Miyano codes that are not set yet. See the comment block at the top of the program."));
  }
  if (unverified.length > 0) {
    writeComment("VERIFY ON THE CONTROL BEFORE RUNNING - " + unverified.join(" "));
  }
}
'''
sub("function onComment(message) {", banner.lstrip("\n") + "\nfunction onComment(message) {")

open(out_path, "w", encoding="utf-8", newline="\n").write(s)
print(f"wrote {out_path}: {s.count(chr(10))} lines; mFormat call sites {n1}, modal call sites {modal_hits}")
