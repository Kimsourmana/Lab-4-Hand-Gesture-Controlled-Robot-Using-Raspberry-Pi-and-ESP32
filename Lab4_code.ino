// ===== MOTOR PIN CONFIGURATION =====
// Motor PWM channels
const int M1_PWM = 33;
const int M2_PWM = 14;
const int M3_PWM = 5;
const int M4_PWM = 19;

// ===== SETUP =====
void setup() {
  Serial.begin(115200);

  // Motor direction pins
  pinMode(25, OUTPUT); pinMode(26, OUTPUT);
  pinMode(27, OUTPUT); pinMode(32, OUTPUT);
  pinMode(18, OUTPUT); pinMode(21, OUTPUT);
  pinMode(22, OUTPUT); pinMode(23, OUTPUT);

  // PWM setup
  ledcSetup(0, 20000, 8); ledcAttachPin(M1_PWM, 0);
  ledcSetup(1, 20000, 8); ledcAttachPin(M2_PWM, 1);
  ledcSetup(2, 20000, 8); ledcAttachPin(M3_PWM, 2);
  ledcSetup(3, 20000, 8); ledcAttachPin(M4_PWM, 3);

  stopMotors();
  Serial.println("[+] Finger Control Robot Ready");
}

// ===== LOOP - SERIAL COMMAND HANDLER =====
void loop() {
  if (Serial.available() > 0) {
    String message = Serial.readStringUntil('\n');
    message.trim();

    int commaPos = message.indexOf(',');
    
    if (commaPos == -1) {
      return;
    }

    String direction = message.substring(0, commaPos);
    String speedText = message.substring(commaPos + 1);

    direction.trim();
    direction.toUpperCase();
    speedText.trim();

    if (speedText.length() == 0 || speedText.length() > 3) {
      return;
    }

    int speed = speedText.toInt();

    if (speed < 0 || speed > 255) {
      return;
    }

    uint8_t pwmSpeed = (uint8_t)speed;

    if (direction == "FORWARD") {
      moveForward(pwmSpeed);
      Serial.println("[>] FORWARD");
    } 
    else if (direction == "BACKWARD") {
      moveBackward(pwmSpeed);
      Serial.println("[>] BACKWARD");
    } 
    else if (direction == "LEFT") {
      turnLeft(pwmSpeed);
      Serial.println("[>] LEFT");
    } 
    else if (direction == "RIGHT") {
      turnRight(pwmSpeed);
      Serial.println("[>] RIGHT");
    } 
    else if (direction == "STOP") {
      stopMotors();
      Serial.println("[>] STOP");
    }
  }
}

// ===== MOTOR CONTROL FUNCTIONS =====

void stopMotors() {
  ledcWrite(0, 0);
  ledcWrite(1, 0);
  ledcWrite(2, 0);
  ledcWrite(3, 0);
}

void moveForward(uint8_t speed) {
  digitalWrite(26, LOW);  digitalWrite(25, HIGH);
  digitalWrite(32, LOW);  digitalWrite(27, HIGH);
  digitalWrite(18, LOW);  digitalWrite(21, HIGH);
  digitalWrite(22, LOW);  digitalWrite(23, HIGH);

  ledcWrite(0, speed);
  ledcWrite(1, speed);
  ledcWrite(2, speed);
  ledcWrite(3, speed);
}

void moveBackward(uint8_t speed) {
  digitalWrite(26, HIGH); digitalWrite(25, LOW);
  digitalWrite(32, HIGH); digitalWrite(27, LOW);
  digitalWrite(18, HIGH); digitalWrite(21, LOW);
  digitalWrite(22, HIGH); digitalWrite(23, LOW);

  ledcWrite(0, speed);
  ledcWrite(1, speed);
  ledcWrite(2, speed);
  ledcWrite(3, speed);
}

void turnLeft(uint8_t speed) {
  digitalWrite(26, HIGH); digitalWrite(25, LOW);
  digitalWrite(32, HIGH); digitalWrite(27, LOW);
  digitalWrite(18, LOW);  digitalWrite(21, HIGH);
  digitalWrite(22, LOW);  digitalWrite(23, HIGH);

  ledcWrite(0, speed);
  ledcWrite(1, speed);
  ledcWrite(2, speed);
  ledcWrite(3, speed);
}

void turnRight(uint8_t speed) {
  digitalWrite(26, LOW);  digitalWrite(25, HIGH);
  digitalWrite(32, LOW);  digitalWrite(27, HIGH);
  digitalWrite(18, HIGH); digitalWrite(21, LOW);
  digitalWrite(22, HIGH); digitalWrite(23, LOW);

  ledcWrite(0, speed);
  ledcWrite(1, speed);
  ledcWrite(2, speed);
  ledcWrite(3, speed);
}