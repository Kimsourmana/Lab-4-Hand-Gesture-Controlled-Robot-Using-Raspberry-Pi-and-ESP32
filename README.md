# Hand Gesture Controlled Robot Using Raspberry Pi and ESP32

## 1. Project Explanation

### Introduction

This project implements a hand gesture-controlled robot using a Raspberry Pi, a USB camera, and an ESP32 microcontroller. It allows users to control the robot's movement through recognized hand gestures without using a physical controller.

### System Operation

The system consists of two main components:

**Raspberry Pi:** The Python application initializes the camera and MediaPipe, captures video frames, detects hand landmarks, and recognizes gestures. A debounce mechanism requires a gesture to remain stable for three processed frames before sending a new movement command. If no hand is detected or the gesture is unknown, the application selects the STOP command.

**ESP32:** The ESP32 initializes the motor direction pins and PWM channels, reads commands through serial communication, parses the movement direction and speed, and controls the four motors accordingly.

The Raspberry Pi sends commands at a baud rate of 115200 using the format `COMMAND,SPEED`, terminated by a newline character. The Flask web server also provides a live camera stream with the detected gesture and serial connection status.

### Hand Gesture Mapping

| Gesture | Robot Action | Serial Command |
|---|---|---|
| V sign | Move forward | `FORWARD,70` |
| Fist | Move backward | `BACKWARD,70` |
| Point left | Turn left | `LEFT,70` |
| Point right | Turn right | `RIGHT,70` |
| Open palm | Stop | `STOP,0` |
| No hand or unknown gesture | Stop | `STOP,0` |

The robot uses a fixed movement speed of 70 for directional movements. The ESP32 uses PWM signals to control motor output and direction pins to determine the direction of rotation.

## 2. System Flowchart

The following flowchart illustrates the complete system workflow, from camera initialization and hand gesture recognition on the Raspberry Pi to serial command processing and motor control on the ESP32.

<img width="2388" height="2608" alt="lab4 drawio" src="https://github.com/user-attachments/assets/d076ce10-976e-4766-8d9b-071c7d72c912" />

## 3. Video Demonstration

**Demonstration video:** [(https://drive.google.com/file/d/1toG4asGozc1V6AjbpX-6Wsk1DQBXc40P/view)]

The video demonstrate:

- Real-time camera feed and hand landmark detection.
- Forward and backward movement.
- Left and right turning.
- Stopping with an open palm.
- Automatic stopping when the hand is removed from the camera.
- Serial commands and ESP32 responses.
- Robot operation at the fixed speed of 70.

### Conclusion

This project demonstrates the integration of computer vision, hand gesture recognition, serial communication, and embedded motor control. It provides a hands-free robot control system and demonstrates communication between a Raspberry Pi and an ESP32.

