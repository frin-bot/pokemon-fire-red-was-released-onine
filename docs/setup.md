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
OK
```

## 3. Arduino Setup

Install Arduino IDE.

Install the Switch controller library:

- `NintendoSwitchControlLibrary`
- Source: https://github.com/lefmarna/NintendoSwitchControlLibrary

Install it through Arduino IDE with **Sketch > Include Library > Add .ZIP Library...**. Do not extract or copy the library files into `arduino/micro_controller/`.

For Switch input to work, the Arduino Micro must compile with a Switch-compatible USB VID/PID. On this Windows setup with Arduino IDE 2.x and Arduino AVR Boards 1.8.7, edit:

```text
C:\Users\efrai\AppData\Local\Arduino15\packages\arduino\hardware\avr\1.8.7\boards.txt
```

In the `micro` section, change these lines:

```text
micro.vid.1=0x0f0d
micro.pid.1=0x0092
micro.build.vid=0x0f0d
micro.build.pid=0x0092
micro.build.usb_manufacturer="HORI CO.,LTD."
micro.build.usb_product="POKKEN CONTROLLER"
```

Restart Arduino IDE after editing `boards.txt`, then re-upload `micro_controller.ino`. Do not change the `micro.upload_port.*` lines; those are used for finding the bootloader/upload port.

Upload order:

1. Upload `arduino/nano_bridge/nano_bridge.ino` to the Arduino Nano.
2. Upload `arduino/micro_controller/micro_controller.ino` to the Arduino Micro.
3. Wire the boards according to `docs/wiring.md`.
4. Test `PING` through the Nano at `57600` baud.
5. Enable wired controller input on the Switch under **System Settings > Controllers and Sensors > Pro Controller Wired Communication**.
6. Open **Controllers > Change Grip/Order** on the Switch.
7. With the Micro USB plugged into the Switch dock, use the Nano Serial Monitor to send `PAIR`. The Micro should reply with `TAPPED L+R`. This sends repeated L+R reports, which is the cleanest registration test for the controller-order screen.
8. After `PAIR`, send `A`, `B`, `HOME`, `PLUS`, `MINUS`, `UP`, `DOWN`, `LEFT`, or `RIGHT`. The Micro should reply with `TAPPED ...`, and the Switch should visibly react to the matching single input.

Manual reset commands:

- `SOFT_RESET` or `SR`: press the game soft-reset combo and stop at the title screen. The Micro replies with `READY_TITLE`.
- `RESET`: press the soft-reset combo, then continue back into the saved game. The Micro replies with `READY_SAVE`.

The Micro sketch sends `pushButton(Button::B, 500, 5)` and repeated L+R reports during `setup()` before it prints `READY`. This mirrors the library example pattern and gives the Switch early button reports so it can register the USB controller after the Micro is plugged in.

The sketch also initializes the Switch controller library before Arduino's USB attach step. Without that early initialization, Windows may show the Micro as `VID_0F0D&PID_0092` with only a serial interface and no gamepad HID interface.

The starter attempt intentionally switches from `A` to repeated `B` presses before the nickname prompt. This avoids accepting the prompt and typing a nickname if timing runs slightly fast. After the nickname prompt is declined, the Micro clears the rival's starter-selection dialogue, opens the in-game menu, enters the Pokemon party, opens the first Pokemon's summary, and leaves that summary sprite stable for the shiny check.

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
.\.venv\Scripts\python.exe scripts\shiny-hunt.py list-cameras --backend any
```

Use the reported camera index in later commands. If Windows shows the capture card in Device Manager but this command only finds the built-in webcam, try the other OpenCV backends:

```powershell
.\.venv\Scripts\python.exe scripts\shiny-hunt.py list-cameras --backend msmf
.\.venv\Scripts\python.exe scripts\shiny-hunt.py list-cameras --backend dshow
```

If the UGREEN capture card opens but does not produce frames, check the physical HDMI signal path before changing software: Switch dock HDMI out to capture-card HDMI in, capture-card pass-through HDMI out to the display if used, Switch awake/docked, and no other app already using the capture card.

## 6. Calibration

Capture a screenshot where the normal starter summary sprite is visible. Use the capture-card or OBS Virtual Camera index reported by `list-cameras`; the examples below use `2`, but replace it with your actual index. For OBS Virtual Camera, request 1080p so the saved calibration frame matches the OBS canvas instead of falling back to a skewed 640x480 frame.

```powershell
.\.venv\Scripts\python.exe scripts\shiny-hunt.py capture-frame --backend any --camera-index 2 --width 1920 --height 1080 --fps 30 --output calibration\starter-normal.png
```

Open `calibration\starter-normal.png` and choose a crop rectangle around the sprite region with visible color differences. The rectangle format is `x,y,width,height`.

Example:

```powershell
.\.venv\Scripts\python.exe scripts\shiny-hunt.py calibrate-image --starter charmander --normal-image calibration\starter-normal.png --crop 444,282,258,284 --output calibration\charmander.json
```

If you also have a known shiny reference image:

```powershell
.\.venv\Scripts\python.exe scripts\shiny-hunt.py calibrate-image --starter charmander --normal-image calibration\starter-normal.png --shiny-image calibration\starter-shiny.png --crop 444,282,258,284 --output calibration\charmander.json
```

Without a shiny reference, the app will classify close matches as `non_shiny` and far matches as `uncertain`. That is still safe because uncertain stops the bot.

## 7. Dry Run

Dry-run mode reads the capture feed and records attempts without sending hardware serial commands:

```powershell
.\.venv\Scripts\python.exe scripts\shiny-hunt.py run --calibration calibration\charmander.json --backend any --camera-index 2 --width 1920 --height 1080 --fps 30 --dry-run --max-attempts 3
```

Check:

- `runs/current/current-run.json`
- `runs/current/attempts.csv`
- `runs/current/screenshots/` for uncertain/shiny frames

## 8. Hardware Run

After dry-run behavior looks correct:

```powershell
.\.venv\Scripts\python.exe scripts\shiny-hunt.py run --calibration calibration\charmander.json --backend any --camera-index 2 --width 1920 --height 1080 --fps 30 --serial-port COM3
```

Replace `COM3` with the Nano's Windows COM port.

The app stops when:

- The frame is classified as `shiny`.
- The frame is classified as `uncertain`.
- The capture feed fails.
- Serial setup fails.

When the frame is classified as `non_shiny`, the app records the attempt, sends `RESET`, waits for the game to return to the save, and starts the next attempt. This is the normal unattended shiny-hunt loop: check first, soft reset only after confirming the starter is not shiny, then try again.

## 9. Timing Adjustment

The Micro sketch includes starter-selection, menu-check, and soft-reset timing constants inside these routines:

- `runStarterAttempt`
- `clearRivalStarterDialogueBeforeCheck`
- `openStarterSummaryForCheck`
- `softResetToSave`

The first real hardware session should be supervised. Adjust delays until the Micro reliably reaches the same check frame every attempt.
