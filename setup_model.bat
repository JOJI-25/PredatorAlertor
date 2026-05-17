@echo off
echo ===================================================
echo  PredatorAlert - Custom 5-Class Model Setup
echo ===================================================
echo.
echo This project uses a custom-trained YOLO model (5class.pt)
echo that detects: tiger, elephant, fox, monkey, wild-boar
echo.
echo 1. Place your "5class.pt" file in the "models" folder
echo 2. Ensure MODEL_PATH=models/5class.pt in your .env file
echo 3. Run "python download_model.py" to verify the setup
echo.
pause
