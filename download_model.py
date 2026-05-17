"""
Script to set up the custom 5-class wildlife detection model.
Classes: tiger, elephant, fox, monkey, wild-boar
Usage: python download_model.py
"""
import os
from pathlib import Path

def setup_model():
    """Check that the custom 5-class model is in place."""
    model_dir = Path("models")
    model_dir.mkdir(exist_ok=True)
    
    model_path = model_dir / "5class.pt"
    
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"✅ Custom 5-class model found at {model_path} ({size_mb:.1f} MB)")
        print(f"   Classes: tiger, elephant, fox, monkey, wild-boar")
    else:
        print("❌ Model not found!")
        print(f"   Please place your '5class.pt' file in the '{model_dir}' folder.")
        print("   Classes: tiger, elephant, fox, monkey, wild-boar")

if __name__ == "__main__":
    setup_model()
