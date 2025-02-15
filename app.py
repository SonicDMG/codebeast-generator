"""
CodeBeast Generator Web Application

A Flask application that generates pixel art mascots from GitHub profile data
using AI-powered image generation and natural language processing.
"""

import os
import logging
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, g
import requests
import logfire
from dotenv import load_dotenv
from dall_e import DallEGenerator

# Load environment variables
load_dotenv(override=True)

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


def run_flow(
    message: str,
    endpoint: str,
    output_type: str = "chat",
    input_type: str = "chat",
    tweaks: Dict[str, Any] = None,
    api_key: str = None
) -> Dict[str, Any]:
    """Execute a Langflow flow with the given parameters.
    
    Args:
        message: Input message for the flow
        endpoint: Flow endpoint or ID
        output_type: Type of output expected
        input_type: Type of input being sent
        tweaks: Optional flow modifications
        api_key: Optional API key for authentication
    
    Returns:
        Dict[str, Any]: Full data dictionary from the flow execution
        
    Raises:
        requests.RequestException: If API request fails
    """
    api_url = f"{BASE_API_URL}/api/v1/run/{endpoint}"

    payload = {
        "input_value": message,
        "output_type": output_type,
        "input_type": input_type,
        "session_id": message.lower() # use the GitHub handle as the session ID
    }
    logger.info("Session ID: %s", payload["session_id"])

    if tweaks:
        payload["tweaks"] = tweaks

    headers = {"x-api-key": api_key} if api_key else None

    response = requests.post(api_url, json=payload, headers=headers, timeout=120)
    response_data = response.json()

    # Extract full response text
    full_response = response_data['outputs'][0]['outputs'][0]['results']['message']['text']

    # Parse response data
    data = parse_langflow_response(full_response)

    # Store data in app context
    if hasattr(g, 'user_data'):
        g.user_data = data

    return data

def parse_langflow_response(full_response: str) -> Dict[str, Any]:
    """Parse the response from Langflow into structured data."""
    parts = full_response.split('|')
    data = {
        'languages': [],
        'prompt': "",
        'github_user_name_url': "",
        'num_repositories': 0
    }

    try:
        # Parse languages
        data['languages'] = [
            lang.strip().strip("'\"")
            for lang in parts[0].split(':')[1].strip('[]').split(',')
            if lang.strip()
        ]

        # Parse other fields
        data['prompt'] = parts[1].split(':', 1)[1].strip()
        data['github_user_name_url'] = parts[2].split(':', 1)[1].strip()
        data['num_repositories'] = int(parts[3].split(':', 1)[1].strip())

    except (IndexError, ValueError) as e:
        logger.error("Failed to parse response parts: %s", str(e))

    return data

@app.route('/')
def home():
    """Render the main application interface."""
    return render_template('index.html')

@app.route('/chat/process', methods=['POST'])
def process_chat():
    """Process GitHub handle and generate AI response.
    
    Returns:
        JSON response containing:
        - response: Generated text description (prompt only)
        - languages: List of programming languages
        - github_url: GitHub URL
        - num_repositories: Number of repositories
        - animal_selection: Selected animal
        - status: Success/error status
        - error: Error message if applicable
    """
    # Clear any existing user data at the start of each request
    if hasattr(g, 'user_data'):
        delattr(g, 'user_data')

    data = request.json
    message = data.get('message')

    try:
        logger.info("Calling Langflow for response")
        user_data = run_flow(
            message=message,
            endpoint=FLOW_ID
        )
        logger.info("Received response from Langflow")
        logger.info("Languages found: %s", user_data.get('languages', []))

        return jsonify({
            'response': user_data['prompt'],
            'languages': user_data.get('languages', []),
            'github_url': user_data.get('github_user_name_url', ''),
            'num_repositories': user_data.get('num_repositories', 0),
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
    port = int(os.getenv('PORT', '5000'))  # Make default a string first
    os.makedirs('static/temp', exist_ok=True)
    app.run(host='0.0.0.0', port=port)
