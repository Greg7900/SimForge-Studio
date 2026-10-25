SimForge Studio V3.0 — Odrive-Wheel wheel + ChrGri active pedals in one app
============================================================================

Wheel: ODrive v3.6 board (MKS ODrive S 56 V, MKS XDrive Mini, ODESC 4.2…) flashed with the Odrive-Wheel
firmware. For the FFBeast firmware, keep SimForge Studio V1.0.
Pedals: ChrGri DIY active pedals (DIY-Sim-Racing-FFB-Pedal), PCB V6, ESP32-S3, over USB.
The pedal firmware is included (firmware folder) and is flashed from SimForge.

GETTING STARTED
  1. Double-click  "SimForge Studio V3.bat"
     The first start installs everything into the .venv folder (2-3 min, Python 3.9+ required).
  2. To try it without the board:  "SimForge Studio V3 (demo).bat"  (simulated board).
  3. To build a standalone .exe:  build_exe.bat  (after a first start).
  Language: English by default, French from the selector at the top right.

  The serial port can only be open in one program at a time: close the Odrive-Wheel web tool,
  odrivetool and the Odrive-Wheel SimHub plugin while SimForge is open.

THE TWO USB LINKS
  LED 1 = serial port: reading/writing settings, commands, console.
  LED 2 = HID: 1 kHz telemetry (position, speed, torque in N·m, motor current, bus voltage and current,
          brake resistor current, temperature, state, errors).

LEFT MENU
  Overview        Wheel and pedals at a glance (state, angle, torque, battery; travel, force in kg and axis
                  sent to the game for each pedal), with a button to the page that sets up each part.

  WHEEL
  Setup           Step-by-step calibrations with checks: precautions, power, errors, motor calibration
                  (resistance/inductance checked), encoder alignment, one-turn CPR check by hand,
                  closed-loop test, recommended automatic start-up for an incremental encoder without index.
  Settings        Every setting, read from the board and read back after each write:
                  Wheel, Game effects (gains, filters, equalizer), Motor and encoder, Power supply,
                  GPIO inputs, Board and profiles. Amber dot = changed, blue = sent,
                  yellow = applied but not stored, red = refused.
                  Wheel/effect settings apply live; ODrive settings wait for “Apply” (those that
                  require it are only written with the motor idle).
                  Consistency checks (alignment kept without index, voltage thresholds, brake resistor,
                  overspeed, current, max torque…).
                  JSON profiles in the Odrive-Wheel web tool format (import/export both ways).
  Monitor         Wheel, torque, currents, voltage, resistor power, temperatures, decoded errors,
                  10 s plots, extremes (voltage sag and peaks), 1 kHz CSV export.
  Encoder         ODrive counters (total count, position in revolution, alignment, direction, phase
                  offset), Z pulse counter, 1 kHz position jump detection.
  PEDALS
  Settings        Each plugged-in pedal shows up by itself (its Brake/Throttle/Clutch role is read from the
                  pedal). Travel, preload and max force in kg, force curve (linear, progressive… presets)
                  with the live pedal dot, test ABS, mechanics, servo.
                  "Apply" = try without saving; "Save to pedal" = stored.
                  Settings are checked the way the firmware does before sending, then read back.
                  "Advanced settings" box: filters, damping, dimensions, game axis curve, messages.
  Firmware        Flashes the pedal firmware (PCB V6) or the wireless receiver, no other software needed.

  TOOLS
  Overlay         Always-on-top window over the game (windowed/borderless): angle, speed, torque N·m and
                  %, bar, peak, saturation, motor current, voltage (and sag), current and power drawn,
                  resistor power, temperature, state. Values or curves.
  Joy tester      Axes, buttons, POV, plot, CSV log (DirectInput).
  Force test      Like ForceTest: every DirectX effect (spring, constant, periodic, friction, damper,
                  inertia, ramp), measured torque in N·m, limited max force, cut-off on overspeed or
                  leaving the range, “does the board respond” test.
  Wheel console   Serial terminal: ODrive commands (r / w / ss / sc…) and OpenFFBoard (class.cmd?).
  Log             Every command sent.

  Bottom bar (wheel pages)  Recenter wheel, Clear errors, DFU mode, Reboot, Save:
                  “Save” stores the wheel/effect settings (sys.save!, no reboot) and, if needed, the ODrive
                  configuration (ss: motor idle, the board reboots and redoes its alignment — let go
                  of the wheel).

PEDALS: GOOD TO KNOW
  - Plug each pedal in through its USB port wired to the serial chip (CH343/CP210x).
  - Close SimHub: it keeps the pedal ports open (one port = one program at a time).
  - SimForge tunes the pedals but does not read game telemetry: in a race, ABS, RPM or slip coming from
    the game need ChrGri's SimHub plugin. Settings made in SimForge and saved to the pedal still apply
    with SimHub.
  - The game sees each pedal as a separate controller: check it in Tools › Joy tester.

SAFETY
  STOP (or Esc) puts the axis in idle: the motor is no longer powered at all, games included, and
  SimForge keeps it idle while STOP is latched. During tests and calibrations, overspeed and leaving
  the range trigger STOP automatically.
  On the board, keep “Cut off on overspeed” enabled with a max speed of 2 to 8 rev/s.
  None of this replaces a hardware power cut-off within reach.

LICENSE
  The Odrive-Wheel firmware is licensed under GPLv3 (see LICENSE-GPLv3.txt next to the firmware).
  SimForge Studio V3 contains no firmware code: it talks to it over USB.
  Pedal firmware (firmware folder): ChrGri and contributors, licence CC BY-NC-SA 4.0 — non-commercial use
  only, attribution required, share alike. Only the build files were changed (see firmware/README.txt and
  build_changes.diff). SimForge's pedal module follows that project's data format, so it carries the same
  non-commercial licence.

If something goes wrong: detailed errors in errors.log next to simforge_studio.py.
