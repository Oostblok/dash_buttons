#include <Wire.h>
#include <AceButton.h>
using namespace ace_button;

#define SLAVE_ADDR 0x45

// Rotary encoder pins
const int ENCODER_CLK = 10;
const int ENCODER_DT  = 16;

// Volume
int volumeLevel = 0;
const int volumeStep = 2;
unsigned long encoderLockUntil = 0;

// Debounce
const unsigned long ENCODER_DEBOUNCE_MS = 20;
unsigned long lastEncoderChange = 0;

uint8_t lastCommandValue = 255; // using 255 as empty/falsy value because 0 is reserved for volume

// Send the last command to pi when requested, latency is determined by the pi
void sendDataToPi() {
  Wire.write(lastCommandValue);
  lastCommandValue = 255;
}

// Button functions, starting from 101 so 0-100 can be reserved for volume
void sendButtonCommand(uint8_t id) {
  lastCommandValue = 100 + id;
}

// Rotary encoder volume
void sendVolume(int vol) {
  lastCommandValue = constrain(vol, 0, 100);
}

// Define buttons
typedef void (*ButtonCallback)();

class Button : public AceButton {
public:
  const char* name;
  ButtonCallback callback;
  Button(uint8_t pin, const char* n, ButtonCallback cb)
    : AceButton(pin), name(n), callback(cb) {}
};

struct ButtonConfigEntry {
  const char* name;
  uint8_t pin;
  ButtonCallback callback;
};

// example buttons
ButtonConfigEntry buttonConfigs[] = {
  {"mode",     4, [](){ sendButtonCommand(1); }},
  {"previous", 5, [](){ sendButtonCommand(2); }},
  {"encoder",  6, [](){ sendButtonCommand(3); }},
  {"next",     7, [](){ sendButtonCommand(4); }},
  {"bright",   8, [](){ sendButtonCommand(5); }}
};

const int numberOfButtons = sizeof(buttonConfigs) / sizeof(buttonConfigs[0]);
Button* buttons[numberOfButtons];

void handleButton(AceButton* ace, uint8_t eventType, uint8_t /*state*/) {
  if (eventType != AceButton::kEventPressed) return;
  Button* button = static_cast<Button*>(ace);
  if (button->callback) button->callback();
}

void receiveDataFromPi(int bytes) {
  int receivedByte = Wire.read();

  if (receivedByte > 0 && receivedByte <= 100) {
    volumeLevel = receivedByte;
   }
}

void setup() {
  Wire.begin(SLAVE_ADDR);
  Wire.onRequest(sendDataToPi);
  Wire.onReceive(receiveDataFromPi);

  pinMode(ENCODER_CLK, INPUT_PULLUP);
  pinMode(ENCODER_DT, INPUT_PULLUP);

  for (int i = 0; i < numberOfButtons; ++i) {
    buttons[i] = new Button(buttonConfigs[i].pin, buttonConfigs[i].name, buttonConfigs[i].callback);
    pinMode(buttonConfigs[i].pin, INPUT_PULLUP);

    ButtonConfig* cfg = buttons[i]->getButtonConfig();
    cfg->setEventHandler(handleButton);
    cfg->setFeature(ButtonConfig::kFeatureClick);
  }
}

void loop() {
  // Check buttons
  for (int i = 0; i < numberOfButtons; ++i) {
    buttons[i]->check();
  }

  // Rotary encoder logic
  static int lastVolumeA = HIGH;
  int currentVolumeA = digitalRead(ENCODER_CLK);
  int currentVolumeB = digitalRead(ENCODER_DT);

  unsigned long now = millis();
  
  if (currentVolumeA != lastVolumeA && currentVolumeA == LOW) {
    encoderLockUntil = now + 100; // lock button

    if (now - lastEncoderChange >= ENCODER_DEBOUNCE_MS) {
      if (currentVolumeB != currentVolumeA) {
        volumeLevel = min(volumeLevel + volumeStep, 100);
      } else {
        volumeLevel = max(volumeLevel - volumeStep, 0);
      }

      lastEncoderChange = now;
      sendVolume(volumeLevel);
    }
  }

  lastVolumeA = currentVolumeA;
  delay(1);
}
