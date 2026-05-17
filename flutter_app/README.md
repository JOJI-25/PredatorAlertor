<div align="center">
  <img src="../linkedin_images/logo.png" alt="PredatorAlert App Logo" width="150">
  <h1>📱 PredatorAlert Mobile App</h1>
  <p><strong>Companion Flutter App for Real-Time Wildlife Alerts and Monitoring</strong></p>

  [![Flutter](https://img.shields.io/badge/Flutter-%2302569B.svg?style=for-the-badge&logo=Flutter&logoColor=white)](#)
  [![Dart](https://img.shields.io/badge/dart-%230175C2.svg?style=for-the-badge&logo=dart&logoColor=white)](#)
  [![Firebase](https://img.shields.io/badge/firebase-%23039BE5.svg?style=for-the-badge&logo=firebase)](#)
  [![Android](https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white)](#)
  [![iOS](https://img.shields.io/badge/iOS-000000?style=for-the-badge&logo=ios&logoColor=white)](#)
</div>

---

## 📖 Overview
The **PredatorAlert Mobile App** is the cross-platform (iOS/Android) companion application for the PredatorAlert Edge AI system. Built using **Flutter**, it acts as the primary user interface for farmers, forest rangers, and rural communities to monitor their camera feeds and receive instantaneous threat notifications.

When the Raspberry Pi edge device detects a predator, this app immediately triggers a high-priority push notification and displays the captured frame with the AI's confidence score.

## ✨ Key Features
- **🚨 Instant Push Notifications:** Get real-time alerts via Firebase Cloud Messaging (FCM) when a predator is detected.
- **📊 Alert Dashboard:** View a historical feed of all detections, categorized by date, priority, and animal type.
- **📷 Image Verification:** View the exact frame captured by the Edge AI, complete with bounding box coordinates and confidence scores.
- **🎥 Live Video Stream:** Connect directly to the Pi's Flask MJPEG server to view the live camera feed in real-time.
- **⚙️ Device Management:** Manage multiple Raspberry Pi edge nodes from a single centralized account.
- **🌙 Dark Mode:** Fully optimized, battery-saving dark mode for night-time monitoring.

## 🛠️ Technology Stack
- **Framework:** Flutter SDK
- **Language:** Dart
- **Backend/Database:** Firebase Firestore & REST APIs
- **Authentication:** Firebase Auth
- **Push Notifications:** Firebase Cloud Messaging (FCM)
- **State Management:** Provider / Riverpod

## 🚀 Installation & Setup

### Prerequisites
- [Flutter SDK](https://docs.flutter.dev/get-started/install) installed on your machine.
- Android Studio or Xcode for device emulation.
- A connected Firebase project configured for Android/iOS.

### Running the App
1. **Navigate to the app directory:**
   ```bash
   cd flutter_app
   ```

2. **Fetch Dependencies:**
   ```bash
   flutter pub get
   ```

3. **Configure Firebase:**
   Ensure you have placed your `google-services.json` (Android) and `GoogleService-Info.plist` (iOS) in their respective directories.

4. **Run the application:**
   ```bash
   flutter run
   ```

## 📱 Screenshots

*(Add screenshots of the mobile app here before final portfolio presentation)*

| Dashboard | Live Stream | Alert Details |
|-----------|-------------|---------------|
| `[Screenshot 1]` | `[Screenshot 2]` | `[Screenshot 3]` |

---

<div align="center">
  <i>Part of the PredatorAlert Edge AI Ecosystem</i>
</div>
