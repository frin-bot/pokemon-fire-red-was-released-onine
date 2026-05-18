# Setup Guide

## 1. Capture Card

Recommended class of device:

- USB HDMI capture card.
- UVC / driver-free behavior.
- 1080p30 or 1080p60 capture.
- Windows compatible.

Suggested purchase target:

- UGREEN 25854 / CM716 HDMI capture card, or similar.

HDMI pass-through is useful but optional. If the card has no pass-through, use the Windows preview while setting up.

## 2. Windows Python Setup

From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
```

Expected test result:

```text
Ran 8 tests
OK
```

## 3. Arduino Setup

Install Arduino IDE.

Install the Switch controller library:

- `NintendoSwitchControlLibrary`
- Source: https://github.com/lefmarna/NintendoSwitchControlLibrary

Install it through Arduino IDE with **Sketch > Include Library > Add .ZIP Library...**. Do not extract or copy the library files into `arduino/micro_controller/`.

Upload order:

1. Upload `arduino/nano_bridge/nano_bridge.ino` to the Arduino Nano.
2. Upload `arduino/micro_controller/micro_controller.ino` to the Arduino Micro.
3. Wire the boards according to `docs/wiring.md`.
4. Test `PING` through the Nano at `57600` baud.

If Arduino reports `multiple definition of pushButton`, `multiple definition of CustomHID`, or similar linker errors, the library is being compiled twice. Check the `arduino/micro_controller/` folder and remove any copied library folders/files such as `src/`, `examples/`, `library.properties`, `LICENSE`, or a library `README.md`. The Micro sketch folder should contain only `micro_controller.ino`; the library should live under the Arduino libraries folder, usually `Documents\Arduino\libraries\NintendoSwitchControlLibrary`.

## 4. Switch Prep

1. Dock the Switch 2.
2. Set display output to a stable 1080p mode for capture.
3. Start Pokemon FireRed.
4. Save directly in front of the selected starter Poke Ball.
5. Leave the Micro disconnected until the sketches and wiring are tested.

## 5. Capture Device Check

With the capture card attached:

```powershell
python scripts\shiny-hunt.py list-cameras
```

Use the reported camera index in later commands.

## 6. Calibration

Capture or save a screenshot where the normal starter check/battle frame is visible. Choose a crop rectangle around the sprite region with visible color differences.

Example:

```powershell
python scripts\shiny-hunt.py calibrate-image --starter charmander --normal-image normal.png --crop 100,100,80,80 --output calibration\charmander.json
```

If you also have a known shiny reference image:

```powershell
python scripts\shiny-hunt.py calibrate-image --starter charmander --normal-image normal.png --shiny-image shiny.png --crop 100,100,80,80 --output calibration\charmander.json
```

Without a shiny reference, the app will classify close matches as `non_shiny` and far matches as `uncertain`. That is still safe because uncertain stops the bot.

## 7. Dry Run

Dry-run mode reads the capture feed and records attempts without sending hardware serial commands:

```powershell
python scripts\shiny-hunt.py run --calibration calibration\charmander.json --camera-index 0 --dry-run --max-attempts 3
```

Check:

- `runs/current/current-run.json`
- `runs/current/attempts.csv`
- `runs/current/screenshots/` for uncertain/shiny frames

## 8. Hardware Run

After dry-run behavior looks correct:

```powershell
python scripts\shiny-hunt.py run --calibration calibration\charmander.json --camera-index 0 --serial-port COM3
```

Replace `COM3` with the Nano's Windows COM port.

The app stops when:

- The frame is classified as `shiny`.
- The frame is classified as `uncertain`.
- The capture feed fails.
- Serial setup fails.

## 9. Timing Adjustment

The Micro sketch includes starter-selection and soft-reset timing constants inside these routines:

- `runStarterAttempt`
- `softResetToSave`

The first real hardware session should be supervised. Adjust delays until the Micro reliably reaches the same check frame every attempt.
