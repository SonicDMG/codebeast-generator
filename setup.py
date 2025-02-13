"""Setup script for CodeBeast Generator"""
import os
import sys
from pathlib import Path

def setup_project():
    """Create necessary directories and check environment"""
    # Create required directories
    Path("static/temp").mkdir(parents=True, exist_ok=True)

    # Check for .env file
    if not os.path.exists(".env"):
        print("Warning: .env file not found. Creating template...")
        with open(".env", "w", encoding="utf-8") as f:
            f.write("""# API Configuration
LANGFLOW_BASE_URL=http://localhost:7860
LANGFLOW_FLOW_ID=your-flow-id
OPENAI_API_KEY=your-openai-key

# Flask Configuration
FLASK_DEBUG=True
FLASK_ENV=development
""")
        print("Please update the .env file with your API keys and configuration.")

    # Check Python version
    if sys.version_info < (3, 8):
        print("Warning: This project requires Python 3.8 or higher")
        sys.exit(1)

    print("Setup complete! Run 'pip install -r requirements.txt' to install dependencies.")

if __name__ == "__main__":
    setup_project()
