#include <ESP32Servo.h>

// --- Hardware Pins ---
#define PIN_FL_A 32
#define PIN_FL_B 33
#define PIN_FR_A 25
#define PIN_FR_B 26
#define PIN_RL_A 27 
#define PIN_RL_B 14
#define PIN_RR_A 12 
#define PIN_RR_B 13

// --- Encoder Pin ---
#define PIN_ENCODER_B 23

// --- Servo (P2) ---
#define PIN_SERVO 2
Servo actionServo;
const int SERVO_MIN_US = 500;
const int SERVO_MAX_US = 2400;
const int SERVO_HOME_ANGLE = 0;
const int SERVO_TARGET_ANGLE = 60;
int servoCurrentAngle = SERVO_HOME_ANGLE;

// --- Mechanical & Encoder Constants ---
const float WHEEL_DIAMETER_METERS = 0.065;
const float COUNTS_PER_WHEEL_REV = 1030.0;
const float WHEEL_CIRCUMFERENCE = PI * WHEEL_DIAMETER_METERS;

// --- Encoder Variables ---
volatile int64_t encoderCount = 0;
int64_t previousEncoderCount = 0;
unsigned long lastEncoderCalcTime = 0;
const unsigned long ENCODER_INTERVAL = 100;
const float SPEED_FILTER_ALPHA = 0.30;
float smoothedSpeed = 0.0;

// --- Motor Speed ---
const int JETSON_SPEED = 200;

#define RXD2 16
#define TXD2 17

// --- Command Timer Variables ---
unsigned long lastCommandTime = 0;
const unsigned long COMMAND_DURATION = 1000; // 1 second (1000 ms)
bool isMoving = false; // Tracks if the car is currently moving

// --- ENCODER ISR ---
void IRAM_ATTR encoderISR() {
  encoderCount++;
}

// --- FORWARD DECLARATIONS ---
void stopAll();
void moveForward(int s);
void moveBackward(int s);
void turnLeft(int s);
void turnRight(int s);
void setServoAngle(int angle);

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2);
  gpio_pullup_en((gpio_num_t)RXD2);

  int pins[] = {32, 33, 25, 26, 27, 14, 12, 13};
  for (int i = 0; i < 8; i++) pinMode(pins[i], OUTPUT);

  pinMode(PIN_ENCODER_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENCODER_B), encoderISR, CHANGE);

  ESP32PWM::allocateTimer(0);
  actionServo.setPeriodHertz(50);
  actionServo.attach(PIN_SERVO, SERVO_MIN_US, SERVO_MAX_US);
  actionServo.write(SERVO_HOME_ANGLE);
  servoCurrentAngle = SERVO_HOME_ANGLE;

  stopAll();

  noInterrupts();
  previousEncoderCount = encoderCount;
  interrupts();
  lastEncoderCalcTime = millis();
  
  // Set last command time in the past so the first command works immediately
  lastCommandTime = millis() - COMMAND_DURATION;

  Serial.println("\n--- CAR READY: SERIAL ONLY MODE ---");
  Serial.println("Commands: F=Forward B=Backward L=Left R=Right S=Stop O=Servo60 C=Servo0");
}

void loop() {
  unsigned long currentTime = millis();

  // --- 1. COMMAND PROCESSING & 1-SECOND LOGIC ---
  if (currentTime - lastCommandTime >= COMMAND_DURATION) {
    // 1-second period has finished. Stop the motors if they were moving.
    if (isMoving) {
      stopAll();
      isMoving = false;
    }

    char cmd = '\0';

    // Read commands from USB Serial
    while (Serial.available() > 0) {
      char c = Serial.read();
      if (isalpha((unsigned char)c)) cmd = toupper(c);
    }

    // Read commands from UART2 (Jetson)
    while (Serial2.available() > 0) {
      char c = Serial2.read();
      if (isalpha((unsigned char)c)) cmd = toupper(c);
    }

    // Execute the command (if any was received)
    if (cmd != '\0') {
      Serial.print("CMD: ");
      Serial.println(cmd);
      switch (cmd) {
        case 'F': moveForward(JETSON_SPEED);  isMoving = true; break;
        case 'B': moveBackward(JETSON_SPEED); isMoving = true; break;
        case 'L': turnLeft(JETSON_SPEED);     isMoving = true; break;
        case 'R': turnRight(JETSON_SPEED);    isMoving = true; break;
        case 'S': stopAll();                  isMoving = false; break;
        case 'O': setServoAngle(SERVO_TARGET_ANGLE); Serial.println("Servo -> 60deg"); isMoving = false; break;
        case 'C': setServoAngle(SERVO_HOME_ANGLE);   Serial.println("Servo -> 0deg");  isMoving = false; break;
      }
      
      // Start the 1-second cooldown/timer for the new command
      lastCommandTime = currentTime;
    }
  } else {
    // We are inside the 1-second window. Actively read and DISCARD incoming bytes.
    // This ignores any multiple/spam commands while the current one is running.
    while (Serial.available() > 0) Serial.read();
    while (Serial2.available() > 0) Serial2.read();
  }

  // --- 2. SPEED CALCULATION (cm/s) ---
  if (currentTime - lastEncoderCalcTime >= ENCODER_INTERVAL) {
    noInterrupts();
    int64_t currentCount = encoderCount;
    interrupts();

    int64_t deltaCount = currentCount - previousEncoderCount;
    previousEncoderCount = currentCount;

    float dt = (currentTime - lastEncoderCalcTime) / 1000.0f;
    float countsPerSecond = (dt > 0.0f) ? (fabsf((float)deltaCount) / dt) : 0.0f;
    float speed_cm_s = (countsPerSecond / COUNTS_PER_WHEEL_REV) * WHEEL_CIRCUMFERENCE * 100.0f;

    smoothedSpeed = (1.0f - SPEED_FILTER_ALPHA) * smoothedSpeed + SPEED_FILTER_ALPHA * speed_cm_s;

    if (deltaCount == 0)               smoothedSpeed = 0.0f;
    if (fabsf(smoothedSpeed) < 0.01f)  smoothedSpeed = 0.0f;

    if (smoothedSpeed != 0.0f) {
      Serial.print("v:"); Serial.println(smoothedSpeed, 2);
      Serial2.print("v:"); Serial2.println(smoothedSpeed, 2);
    }

    lastEncoderCalcTime = currentTime;
  }
}

// --- SERVO ---
void setServoAngle(int angle) {
  angle = constrain(angle, 0, 180);
  actionServo.write(angle);
  servoCurrentAngle = angle;
}

// --- MOTORS ---
void moveBackward(int s) {
  digitalWrite(PIN_FL_B, LOW); analogWrite(PIN_FL_A, s);
  digitalWrite(PIN_FR_A, LOW); analogWrite(PIN_FR_B, s);
  digitalWrite(PIN_RR_A, LOW); analogWrite(PIN_RR_B, s);
  digitalWrite(PIN_RL_B, LOW); analogWrite(PIN_RL_A, s);
}

void moveForward(int s) {
  digitalWrite(PIN_FL_A, LOW); analogWrite(PIN_FL_B, s);
  digitalWrite(PIN_FR_B, LOW); analogWrite(PIN_FR_A, s);
  digitalWrite(PIN_RR_B, LOW); analogWrite(PIN_RR_A, s);
  digitalWrite(PIN_RL_A, LOW); analogWrite(PIN_RL_B, s);
}

void turnRight(int s) {
  digitalWrite(PIN_FL_B, LOW); analogWrite(PIN_FL_A, s);
  digitalWrite(PIN_FR_B, LOW); analogWrite(PIN_FR_A, s);
  digitalWrite(PIN_RR_B, LOW); analogWrite(PIN_RR_A, s);
  digitalWrite(PIN_RL_B, LOW); analogWrite(PIN_RL_A, s);
}

void turnLeft(int s) {
  digitalWrite(PIN_FL_A, LOW); analogWrite(PIN_FL_B, s);
  digitalWrite(PIN_FR_A, LOW); analogWrite(PIN_FR_B, s);
  digitalWrite(PIN_RR_A, LOW); analogWrite(PIN_RR_B, s);
  digitalWrite(PIN_RL_A, LOW); analogWrite(PIN_RL_B, s);
}

void stopAll() {
  int p[] = {32, 33, 25, 26, 27, 14, 12, 13};
  for (int i = 0; i < 8; i++) { digitalWrite(p[i], LOW); analogWrite(p[i], 0); }
}