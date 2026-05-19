#include <NintendoSwitchControlLibrary.h>

const long BAUD_RATE = 57600;
const unsigned long SERIAL_POLL_MS = 10;
const int LED_PIN = 17;

String inputLine = "";
bool stopRequested = true;

void setup() {
  Serial1.begin(BAUD_RATE);
  pinMode(LED_PIN, OUTPUT);
  delay(3000);
  registerControllerWithSwitch();
  blinkReadyLed();
  sendStatus("READY");
}

void loop() {
  readSerialCommands();
}

void readSerialCommands() {
  while (Serial1.available() > 0) {
    char ch = (char)Serial1.read();
    if (ch == '\r') {
      continue;
    }
    if (ch == '\n') {
      handleCommand(inputLine);
      inputLine = "";
      continue;
    }
    if (inputLine.length() < 80) {
      inputLine += ch;
    }
  }
}

void handleCommand(String command) {
  command.trim();
  command.toLowerCase();

  if (command == "ping") {
    sendStatus("PONG");
    return;
  }

  if (command.startsWith("stop")) {
    stopRequested = true;
    sendStatus("STOPPED");
    return;
  }

  if (handleDiagnosticCommand(command)) {
    return;
  }

  if (command.startsWith("start ")) {
    stopRequested = false;
    String starter = command.substring(6);
    sendStatus("BUSY START");
    runStarterAttempt(starter);
    if (!stopRequested) {
      sendStatus("READY_CHECK");
    }
    return;
  }

  if (command == "reset") {
    stopRequested = false;
    sendStatus("BUSY RESET");
    softResetToSave();
    if (!stopRequested) {
      sendStatus("READY_SAVE");
    }
    return;
  }

  sendStatus("ERR UNKNOWN_COMMAND");
}

void registerControllerWithSwitch() {
  // The Switch often needs early reports before it accepts the USB HID controller.
  pushButton(Button::B, 500, 5);
  delay(500);
}

void blinkReadyLed() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, LOW);
    delay(200);
    digitalWrite(LED_PIN, HIGH);
    delay(200);
  }
}

bool handleDiagnosticCommand(String command) {
  if (command == "a") {
    tapDiagnosticButton(Button::A, "TAPPED A");
    return true;
  }
  if (command == "b") {
    tapDiagnosticButton(Button::B, "TAPPED B");
    return true;
  }
  if (command == "home") {
    tapDiagnosticButton(Button::HOME, "TAPPED HOME");
    return true;
  }
  if (command == "up") {
    tapDiagnosticHat(Hat::UP, "TAPPED UP");
    return true;
  }
  if (command == "down") {
    tapDiagnosticHat(Hat::DOWN, "TAPPED DOWN");
    return true;
  }
  if (command == "left") {
    tapDiagnosticHat(Hat::LEFT, "TAPPED LEFT");
    return true;
  }
  if (command == "right") {
    tapDiagnosticHat(Hat::RIGHT, "TAPPED RIGHT");
    return true;
  }
  return false;
}

void tapDiagnosticButton(uint16_t button, const char* status) {
  stopRequested = false;
  pushButton(button);
  waitInterruptible(300);
  sendStatus(status);
}

void tapDiagnosticHat(uint8_t hat, const char* status) {
  stopRequested = false;
  pushHat(hat);
  waitInterruptible(300);
  sendStatus(status);
}

void runStarterAttempt(String starter) {
  starter.trim();

  // Assumption: the save is facing the selected starter Poke Ball.
  tap(Button::A, 900);       // Inspect the ball.
  tap(Button::A, 700, 4);    // Advance Oak's text.
  tap(Button::A, 1000);      // Confirm the starter choice when Yes is selected.
  tap(Button::A, 700, 8);    // Receive the Pokemon and reach nickname prompt.
  tap(Button::B, 900);       // Decline nickname when possible.
  tap(Button::A, 700, 16);   // Advance rival dialogue and battle intro.

  // This pause leaves the battle/send-out frames stable for the capture script.
  waitInterruptible(3000);
}

void softResetToSave() {
  pressSoftResetCombo();
  waitInterruptible(5500);   // Title screen.
  tap(Button::A, 1500);      // Start title/menu flow.
  tap(Button::A, 2500);      // Continue from save.
  tap(Button::A, 1500);      // Clear any startup text.
}

void pressSoftResetCombo() {
  if (stopRequested) {
    return;
  }

  SwitchControlLibrary().pressButton(Button::A);
  SwitchControlLibrary().pressButton(Button::B);
  SwitchControlLibrary().pressButton(Button::PLUS);
  SwitchControlLibrary().pressButton(Button::MINUS);
  SwitchControlLibrary().sendReport();
  waitInterruptible(700);
  SwitchControlLibrary().releaseButton(Button::A);
  SwitchControlLibrary().releaseButton(Button::B);
  SwitchControlLibrary().releaseButton(Button::PLUS);
  SwitchControlLibrary().releaseButton(Button::MINUS);
  SwitchControlLibrary().sendReport();
  waitInterruptible(700);
}

void tap(uint16_t button, unsigned long afterMs) {
  tap(button, afterMs, 1);
}

void tap(uint16_t button, unsigned long afterMs, int count) {
  for (int i = 0; i < count; i++) {
    if (stopRequested) {
      return;
    }
    pushButton(button);
    waitInterruptible(afterMs);
  }
}

bool waitInterruptible(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    pollStopCommand();
    if (stopRequested) {
      return false;
    }
    delay(SERIAL_POLL_MS);
  }
  return true;
}

void pollStopCommand() {
  while (Serial1.available() > 0) {
    char ch = (char)Serial1.read();
    if (ch == '\r') {
      continue;
    }
    if (ch == '\n') {
      String command = inputLine;
      inputLine = "";
      command.trim();
      command.toLowerCase();
      if (command.startsWith("stop")) {
        stopRequested = true;
        sendStatus("STOPPED");
      }
      return;
    }
    if (inputLine.length() < 80) {
      inputLine += ch;
    }
  }
}

void sendStatus(const char* message) {
  Serial1.println(message);
}
