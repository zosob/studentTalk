#!/usr/bin/env python3
"""
Student Chatbot Startup Script
"""

import subprocess
import sys
import time
import requests
import os


def check_ollama():
    """Check if Ollama is running and has the required model"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Ollama is not running. Please start it with 'ollama serve'")
            return False

        if 'llama3.1:8b' not in result.stdout:
            print("\U0001f4e5 Downloading llama3.1:8b model (this may take a few minutes)...")
            download_result = subprocess.run(['ollama', 'pull', 'llama3.1:8b'])
            if download_result.returncode != 0:
                print("❌ Failed to download model")
                return False

        print("✅ Ollama and model are ready")
        return True
    except FileNotFoundError:
        print("❌ Ollama not found. Please install Ollama first.")
        return False


def check_database():
    """Check database connection and create tables"""
    try:
        from database import engine, init_db
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        init_db()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Set DATABASE_URL in a .env file (see .env.example)")
        return False


def install_requirements():
    """Install required Python packages"""
    packages = [
        'fastapi',
        'uvicorn[standard]',
        'websockets',
        'sentence-transformers',
        'textblob',
        'vaderSentiment',
        'PyPDF2',
        'faiss-cpu',
        'ollama',
        'python-multipart',
        'sqlalchemy',
        'psycopg2-binary',
        'python-dotenv',
    ]

    print("\U0001f4e6 Installing required packages...")
    for package in packages:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                           check=True, capture_output=True)
            print(f"✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False

    return True


def start_server():
    """Start the FastAPI server"""
    print("\U0001f680 Starting chatbot server...")
    print("\U0001f4dd Access the chatbot at: http://localhost:8000")
    print("\U0001f4ca Wellbeing dashboard at: http://localhost:8000/wellbeing_dashboard")
    print("\n\U0001f504 Press Ctrl+C to stop the server\n")

    try:
        import uvicorn
        from main import app
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n\U0001f44b Server stopped")
    except ImportError:
        print("❌ Could not import required modules. Please check your installation.")


def main():
    print("\U0001f393 Student Chatbot Setup")
    print("=" * 40)

    if 'student-chatbot' not in os.environ.get('CONDA_DEFAULT_ENV', ''):
        print("⚠️  Warning: You might not be in the 'student-chatbot' conda environment")
        print("   Run: conda activate student-chatbot")
        print("")

    if not install_requirements():
        print("❌ Failed to install requirements")
        return

    if not check_ollama():
        print("❌ Ollama setup failed")
        return

    if not check_database():
        print("❌ Database setup failed")
        return

    start_server()


if __name__ == "__main__":
    main()
