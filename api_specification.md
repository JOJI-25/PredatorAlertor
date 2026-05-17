# API Specification: Raspberry Pi to Backend

## 1. The API Endpoint
The Raspberry Pi acts as a Client. It sends data TO the backend.

- **URL**: `https://predatoralert.onrender.com/api/detections`
- **Method**: `POST`

## 2. Authorization
You must include the API key in the headers.

- **Header**: `Authorization: Bearer device_key_01`

## 3. The JSON Data Format
This is the exact JSON structure the Pi sends.

### Example JSON Payload:
```json
{
  "device_id": "pi_camera_01",
  "animal": "Elephant",
  "confidence": 0.92,
  "timestamp": "2026-01-06T19:40:00",
  "image_base64": "..."
}
```

### Field Details:
- **device_id** (String): Who is sending this? (e.g., "pi_camera_01")
- **animal** (String): What did we see? (e.g., "Elephant")
- **confidence** (Float): How sure are we? (0.0 to 1.0)
- **image_base64** (String): The actual image file, converted to a text string.
