# Shiny Starter Automation Design

## Goal

Build a fully unattended, non-invasive shiny starter hunting setup for the Nintendo Switch release of Pokemon FireRed. The system repeatedly selects a starter, checks whether it is shiny from captured video, resets if it is not shiny, and stops safely when a shiny or uncertain result is detected.

This design uses controller input automation and video analysis only. It does not modify the game, inspect memory, alter save data, or bypass software protections.

## Confirmed Context

Pokemon FireRed and Pokemon LeafGreen are available as standalone Nintendo Switch releases that are playable on Nintendo Switch 2 systems. The system design should treat the game as Switch software running through the normal dock/display/controller path, not as a Nintendo Switch Online GBA app.

Relevant public references:

- Nintendo official product page: https://www.nintendo.com/us/store/products/english-pokemon-firered-version-switch/
- Pokemon.com release article: https://www.pokemon.com/uk/pokemon-news/play-the-pokemon-firered-version-and-pokemon-leafgreen-version-games-on-nintendo-switch-systems

## Selected Approach

Use a Windows computer, USB HDMI capture card, Arduino Micro, and Arduino Nano serial bridge.

The Windows computer is the control brain. It reads the HDMI capture feed, runs computer vision, counts attempts, logs results, and sends simple run/reset/stop commands.

The Arduino Micro is the Switch-facing controller. It plugs into the Switch 2 dock over USB and sends a deterministic sequence of controller inputs.

The Arduino Nano is the PC-facing serial bridge. It plugs into the Windows computer over USB and relays serial commands to the Arduino Micro over jumper/ribbon wires.

## Hardware Layout

Required hardware:

- Nintendo Switch 2 docked with Pokemon FireRed installed.
- Windows laptop or desktop that can stay awake near the Switch.
- USB HDMI capture card, preferably plug-and-play UVC, 1080p30 or 1080p60.
- Arduino Micro.
- Arduino Nano V3.0.
- Ribbon/jumper wires.
- USB cables and adapters.

Recommended wiring:

- Nano USB connects to Windows.
- Micro USB connects to the Switch 2 dock.
- Nano `D11` connects to Micro `RX1` / `D0`.
- Nano `D10` connects to Micro `TX1` / `D1`.
- Nano `GND` connects to Micro `GND`.

The Nano uses `SoftwareSerial` on D10/D11 because the Nano hardware UART is shared with the USB serial chip. The exact Arduino board pin labels must still be confirmed before wiring because clone boards sometimes label serial pins differently.

## Software Components

### Windows Automation App

The Windows app is a Python program using OpenCV and pyserial. It owns the hunt state and provides:

- Capture card device selection.
- Starter selection: Bulbasaur, Charmander, or Squirtle.
- Calibration mode for crop regions and expected normal/shiny color profiles.
- Live hunt mode.
- Dry-run mode that detects and logs without sending reset commands.
- Attempt counter.
- Per-attempt logging.
- Final shiny-found summary.

### Arduino Micro Controller Firmware

The Micro firmware emulates a Switch-compatible controller using a suitable Arduino Switch control library. It receives compact serial commands from the Nano and runs predefined input routines:

- Navigate from the saved starting position to choose the selected starter.
- Advance dialogue until the shiny check screen is visible.
- Soft reset or return to the known start state after a non-shiny result.
- Stop all inputs immediately on `STOP`.

### Arduino Nano Bridge Firmware

The Nano firmware acts as a simple USB serial to TTL serial bridge:

- Reads commands from Windows over USB serial.
- Forwards commands to the Micro.
- Optionally forwards status lines from the Micro back to Windows.

This keeps the Micro's USB port dedicated to the Switch while still allowing Windows to coordinate the hunt.

## Automation Flow

The player prepares the save manually:

1. Start Pokemon FireRed.
2. Stand directly in front of the chosen starter Poke Ball.
3. Save the game.
4. Start the automation system.

For each attempt:

1. Windows increments the run state to start a new attempt.
2. Windows sends `START_ATTEMPT` to the Nano.
3. The Nano forwards the command to the Micro.
4. The Micro performs the starter selection input sequence.
5. The Micro advances to the screen where the starter's colors can be evaluated.
6. Windows captures frames from the HDMI capture card.
7. Windows waits until the expected check screen is stable.
8. Windows evaluates the configured crop region.
9. If the result is confidently non-shiny, Windows logs the attempt and sends `RESET`.
10. If the result is shiny, Windows logs the attempt, saves a screenshot, sends `STOP`, and ends the run.
11. If the result is uncertain, Windows logs the uncertainty, saves a screenshot, sends `STOP`, and pauses for human review.

The system must prefer false stops over false resets. Resetting over a shiny is the failure mode to avoid.

## Shiny Detection

Detection should use a calibration-based OpenCV pipeline rather than hard-coded assumptions alone.

The first calibration step captures the selected starter's normal appearance from the user's Switch/capture setup. The user confirms a crop region that contains the sprite or summary area where the color difference is visible. The app stores:

- Starter name.
- Capture resolution.
- Crop rectangle.
- Normal color statistics.
- Optional shiny reference statistics if available from a known screenshot.
- Confidence thresholds.

During live hunting, the app compares the captured crop to expected normal and shiny profiles. It can use a combination of:

- Average color in selected regions.
- HSV histogram distance.
- Masked color ranges for starter-specific shiny colors.
- Screen stability checks to avoid reading during transitions.

Initial starter-specific detection should be conservative:

- Bulbasaur: shiny palette shifts toward yellow-green.
- Charmander: shiny palette shifts toward warmer/golder orange.
- Squirtle: shiny palette shifts toward lighter blue/green shell differences.

Exact thresholds are calibrated locally from the capture feed.

## Attempt Counting And Logging

Attempt counting is a core feature.

The app records one attempt when it reaches the detection screen and evaluates the starter. It does not count partial startup failures before the check screen.

Persistent state should be written after every evaluated attempt to avoid losing progress if the app closes or Windows restarts.

Suggested files:

- `runs/current-run.json`
- `runs/attempts.csv`
- `runs/screenshots/attempt-000123.png`
- `runs/shiny-found.json`

Each attempt log entry includes:

- Attempt number.
- Timestamp.
- Starter.
- Detection result: `non_shiny`, `shiny`, or `uncertain`.
- Confidence score.
- Screenshot path, at least for shiny and uncertain attempts.
- Optional frame analysis details for debugging.

When shiny is found, the app writes a final summary with the starter, total attempts, timestamp, detection confidence, and screenshot path.

## Safety Rules

The automation must follow these rules:

- If detection confidence is below threshold, stop.
- If the capture card feed freezes, stop.
- If the expected screen is not found in time, stop.
- If serial communication fails, stop.
- If the Micro reports an error, stop.
- If the user presses a keyboard panic key, stop.
- Never reset after a `shiny` or `uncertain` result.

The Micro should stop sending inputs when it receives `STOP` and should not resume until Windows sends a new explicit start command.

## Verification Plan

Before running a real hunt:

1. Confirm Nano-to-Micro wiring with a serial echo test.
2. Confirm the Micro can send safe controller inputs to the Switch.
3. Confirm the capture card appears as a camera device in Windows.
4. Confirm OpenCV can read stable frames from the capture card.
5. Run calibration for the chosen starter.
6. Run dry-run mode without resets and confirm the app recognizes the check screen.
7. Run a short controlled loop where the app logs attempts but requires manual confirmation before resetting.
8. Enable full unattended reset only after the log and screenshots match expectations.

## Deliverables

The implementation should produce:

- Arduino Micro controller sketch.
- Arduino Nano serial bridge sketch.
- Windows Python automation script.
- Calibration workflow.
- Run logging and attempt counter.
- Wiring and setup guide.
- Troubleshooting checklist.

## Open Decisions For Implementation

These details will be finalized during implementation:

- Exact Switch-compatible Arduino controller library.
- Exact starter input timings for the Switch release.
- Whether soft reset is available and reliable in the Switch release, or whether the loop should use Home/close/reopen behavior.
- Exact OpenCV detection thresholds after calibration.
- Final capture-card device selection method on Windows.
