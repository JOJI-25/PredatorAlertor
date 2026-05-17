# 🚀 Deploying to Raspberry Pi 5

## 0. Prerequisite: Install Dependencies
Run this command on your Raspberry Pi to install the required ONNX libraries:
```bash
pip3 install onnx onnxruntime --break-system-packages
```
*(Note: The `--break-system-packages` flag is necessary on newer Raspberry Pi OS versions if you are not using a virtual environment)*

## 1. Code Sync
Ensure your Raspberry Pi has the latest code files. If you are copying manually, make sure to update:
- `detector.py`
- `config.py`
- `api_client.py`

## 2. Model Setup (Crucial!)
Your logs show the Pi is still trying to load `best.pt`. You must configure it to use the optimized ONNX model.

### A. Copy the Model
Transfer `models/best.onnx` from your computer to the Pi:
```bash
# Run this on your WINDOWS machine (PowerShell)
scp .\models\best.onnx pi@raspberrypi:~/predator_alert/models/
```
*(Replace `pi@raspberrypi` with your actual Pi username/hostname)*

### B. Update Configuration
On your **Raspberry Pi**, edit the `.env` file to point to the new model:

```bash
nano .env
```

Change the `MODEL_PATH` line:
```ini
# Change this
MODEL_PATH=models/best.pt

# To this
MODEL_PATH=models/best.onnx
```

Also add these ONNX optimizations to `.env`:
```ini
INFERENCE_IMGSZ=640
ONNX_NUM_THREADS=4
```

## 3. Fix API Connection `ERROR: Request timeout` 
The logs show `Request timeout`. This happens because the Pi is likely trying to send alerts to `localhost` or an incorrect IP.

**The Issue**: `localhost` on the Pi refers to the Pi itself. Your backend is running on your **Laptop**.

**The Fix**:
1. Find your Laptop's IP address (run `ipconfig` on Windows). It will look like `192.168.31.XX`.
2. Update `.env` on the Raspberry Pi:

```ini
# Replace localhost with your Production Backend URL
API_URL=https://predatoralert.onrender.com
```

## 4. Verification
Run the system again:
```bash
python3 main.py
```

Check for:
- `INFO: API | Loading ONNX model... | path=models/best.onnx`
- `INFO: API | Sent successfully` (instead of timeout)
