"""
CodeBeast Generator Web Application

A Flask application that generates pixel art mascots from GitHub profile data
using AI-powered image generation and natural language processing.
"""

import os
import logging
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify
import requests
import logfire
from dotenv import load_dotenv
from dall_e import DallEGenerator

# Load environment variables
load_dotenv()

# Initialize logging
logfire.configure()
logging.basicConfig(handlers=[logfire.LogfireLoggingHandler()])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuration from environment
BASE_API_URL = os.getenv('LANGFLOW_BASE_URL')
FLOW_ID = os.getenv('LANGFLOW_FLOW_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not all([BASE_API_URL, FLOW_ID, OPENAI_API_KEY]):
    raise ValueError("Missing required environment variables. Check .env file.")

# Initialize Flask app
app = Flask(__name__)
logfire.instrument_flask(app)
app.static_folder = 'static'

# Initialize DALL-E generator
dalle = DallEGenerator(OPENAI_API_KEY)

def run_flow(message: str, endpoint: str, output_type: str = "chat",
            input_type: str = "chat", tweaks: Dict[str, Any] = None,
            api_key: str = None) -> str:
    """Execute a Langflow flow with the given parameters.
    
    Args:
        message: Input message for the flow
        endpoint: Flow endpoint or ID
        output_type: Type of output expected
        input_type: Type of input being sent
        tweaks: Optional flow modifications
        api_key: Optional API key for authentication
    
    Returns:
        str: Flow execution response
        
    Raises:
        requests.RequestException: If API request fails
    """
    api_url = f"{BASE_API_URL}/api/v1/run/{endpoint}"

    payload = {
        "input_value": message,
        "output_type": output_type,
        "input_type": input_type,
    }

    if tweaks:
        payload["tweaks"] = tweaks

    headers = {"x-api-key": api_key} if api_key else None

    response = requests.post(api_url, json=payload, headers=headers, timeout=120)
    response_data = response.json()

    return response_data['outputs'][0]['outputs'][0]['results']['message']['text']

@app.route('/')
def home():
    """Render the main application interface."""
    return render_template('index.html')

@app.route('/chat/process', methods=['POST'])
def process_chat():
    """Process GitHub handle and generate AI response.
    
    Returns:
        JSON response containing:
        - response: Generated text description
        - status: Success/error status
        - error: Error message if applicable
    """
    data = request.json
    message = data.get('message')

    try:
        logger.info("Calling Langflow for response")
        response = run_flow(
            message=message,
            endpoint=FLOW_ID
        )
        logger.info("Received response from Langflow")

        return jsonify({
            'response': response,
            'status': 'success'
        })

    except requests.RequestException as e:
        logger.error("API request error: %s", str(e))
        return jsonify({
            'error': str(e),
            'status': 'error'
        })

@app.route('/chat/generate-image', methods=['POST'])
def generate_image():
    """Generate pixel art mascot from AI description.
    
    Returns:
        JSON response containing:
        - image_url: Path to generated image
        - status: Success/error status
        - error: Error message if applicable
    """
    data = request.json
    prompt = data.get('prompt')

    try:
        logger.info("Starting DALL-E image generation")
        image = dalle.generate_image(
            prompt=prompt,
            size="1024x1024"
        )

        logger.info("Saving generated image")
        img_path = 'static/temp/generated.png'
        image.save(img_path)

        return jsonify({
            'image_url': img_path,
            'status': 'success'
        })

    except (requests.RequestException, ConnectionError) as e:
        logger.error("Image generation error: %s", str(e))
        return jsonify({
            'error': str(e),
            'status': 'error'
        })

if __name__ == '__main__':
    os.makedirs('static/temp', exist_ok=True)
    app.run(debug=True)
