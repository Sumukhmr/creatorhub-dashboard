"""
CreatorHub - Content Tools Dashboard
====================================

A unified Flask dashboard combining multiple content creation tools:
- Audio Generator (ElevenLabs TTS)
- Explainer Generator (Gemini AI)  
- Image Reducer (Smart Compression)
- Image Renamer (Bulk Rename)

Author: CreatorHub Team
Version: 1.0.0
License: MIT

This application provides a web-based interface for content creators
to generate audio, create lesson explanations, compress images, and
bulk rename files - all from a single dashboard.

Requirements:
- Python 3.8+
- Flask 3.0+
- See requirements.txt for full dependencies

Usage:
    1. Set up environment variables in .env file
    2. Install dependencies: pip install -r requirements.txt
    3. Run: python app.py
    4. Open: http://localhost:5000
"""

# =============================================================================
# IMPORTS
# =============================================================================

from flask import Flask, Blueprint, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import re
import json
import time
import tempfile
import platform
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Third-party imports
import requests
from PIL import Image
import google.generativeai as genai

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables from .env file
load_dotenv()

# API Keys (loaded from environment variables for security)
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Gemini if API key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ElevenLabs Voice Configuration
# Each voice has a unique ID and language-specific suffixes for file naming
VOICES = {
    'french': {
        'id': 'vTGV06pygfwa2WhLDZFp',
        'name': 'French Darling',
        'native_suffix': '_french',
        'english_suffix': '_english_frenchvoice'
    },
    'english': {
        'id': 'jB2lPb5DhAX6l1TLkKXy',
        'name': 'Sophia',
        'native_suffix': '_english',
        'english_suffix': '_english'
    },
    'spanish': {
        'id': 'T4Au24Lt2uWk24Qra0No',
        'name': 'Spanish Voice',
        'native_suffix': '_spanish',
        'english_suffix': '_english_spanishvoice'
    },
    'german': {
        'id': 'rKiu7lQ4c5P3az3745s3',
        'name': 'Benjamin',
        'native_suffix': '_german',
        'english_suffix': '_english_germanvoice'
    }
}

# ElevenLabs model configuration
ELEVENLABS_MODEL_ID = "eleven_v3"

# Image compression settings
IMAGE_TARGET_SIZE = 500 * 1024  # 500KB target
IMAGE_MAX_DIMENSION = 2000  # Maximum width/height
IMAGE_QUALITY_START = 85  # Starting JPEG quality
IMAGE_QUALITY_MIN = 30  # Minimum JPEG quality
IMAGE_QUALITY_STEP = 5  # Quality reduction step

# Temporary upload folder for image processing
UPLOAD_FOLDER = tempfile.mkdtemp()

# Default output folder for renamed images
DEFAULT_OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'renamed_images')

# Supported languages for explainer generator
SUPPORTED_LANGUAGES = [
    'French', 'Spanish', 'German', 'Italian', 'Portuguese',
    'Japanese', 'Mandarin Chinese', 'Korean', 'Arabic', 'Russian'
]

# =============================================================================
# FLASK APPLICATION SETUP
# =============================================================================

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

# =============================================================================
# BLUEPRINTS
# =============================================================================

audio_bp = Blueprint('audio', __name__)
explainer_bp = Blueprint('explainer', __name__)
image_bp = Blueprint('image', __name__)
renamer_bp = Blueprint('renamer', __name__)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_audio_folder():
    """
    Get or create the folder for storing generated audio files.
    
    Returns:
        Path: Path object pointing to the audio folder
    """
    audio_folder = Path(__file__).parent.resolve() / "static" / "audio"
    audio_folder.mkdir(parents=True, exist_ok=True)
    return audio_folder


def parse_text_blocks(text, selected_voice):
    """
    Parse text to extract blocks based on curly braces.
    
    Text wrapped in { } is treated as native language.
    Plain text is treated as English.
    
    Args:
        text (str): Input text with optional curly brace markers
        selected_voice (str): The selected voice/language
        
    Returns:
        list: List of tuples (is_native, content)
    """
    blocks = []
    i = 0
    
    while i < len(text):
        # Skip whitespace
        while i < len(text) and text[i] in ' \t':
            i += 1
        
        if i >= len(text):
            break
        
        # Check for native language block (in curly braces)
        if text[i] == '{':
            start = i + 1
            i += 1
            while i < len(text) and text[i] != '}':
                i += 1
            if i < len(text):
                content = text[start:i].strip()
                if content:
                    blocks.append((True, content))
                i += 1
            continue
        
        # Skip newlines
        elif text[i] == '\n':
            i += 1
            continue
        
        # English text (plain, no braces)
        else:
            start = i
            while i < len(text) and text[i] not in '\n{':
                i += 1
            content = text[start:i].strip()
            if content:
                blocks.append((False, content))
            if i < len(text) and text[i] == '\n':
                i += 1
    
    return blocks


def text_to_filename(text, selected_voice, is_native):
    """
    Convert text to a safe filename format.
    
    Args:
        text (str): The text to convert
        selected_voice (str): Selected voice/language
        is_native (bool): Whether this is native language text
        
    Returns:
        str: Safe filename (without extension)
    """
    # Take first 10 words
    words = text.strip().replace('\n', ' ').split()[:10]
    filename = "_".join(words)
    filename = filename.lower()
    
    # Remove special characters
    filename = "".join(c if c.isalnum() or c == "_" else "_" for c in filename)
    filename = "_".join(filter(None, filename.split("_")))
    
    # Add language suffix
    if is_native:
        suffix = VOICES[selected_voice]['native_suffix']
    else:
        suffix = VOICES[selected_voice]['english_suffix']
    
    return filename + suffix


def text_to_speech(text, output_path, voice_id):
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        text (str): Text to convert to speech
        output_path (Path): Path to save the audio file
        voice_id (str): ElevenLabs voice ID
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    if not ELEVENLABS_API_KEY:
        return False, "API key not configured"
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 1.0,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
            "speed": 1.0
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True, None
        else:
            return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)


def sanitize_filename(filename):
    """
    Remove or replace special characters in filename.
    
    Handles accented characters, spaces, and other special chars.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename safe for all filesystems
    """
    name, ext = os.path.splitext(filename)
    safe_name = re.sub(r'[^\w\-_.]', '_', name)
    return f"{safe_name}{ext}"


def compress_image(file):
    """
    Compress an image to reach target file size (~500KB).
    
    Uses iterative quality reduction and optional downscaling.
    
    Args:
        file: Flask file object
        
    Returns:
        dict: Compression results including sizes and dimensions
    """
    try:
        # Read the image
        img = Image.open(file)
        file.seek(0, 2)
        original_size = file.tell()
        file.seek(0)
        
        # Create new filename with "1" suffix
        original_filename = file.filename
        name, ext = os.path.splitext(original_filename)
        new_filename = f"{name}1{ext}"
        safe_filename = sanitize_filename(new_filename)
        
        # Convert to RGB if needed (handle transparency)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Downscale if image is too large
        if max(img.size) > IMAGE_MAX_DIMENSION:
            img.thumbnail((IMAGE_MAX_DIMENSION, IMAGE_MAX_DIMENSION), Image.Resampling.LANCZOS)
        
        # Iterative compression
        quality = IMAGE_QUALITY_START
        output = io.BytesIO()
        
        while True:
            output.seek(0)
            output.truncate(0)
            
            img.save(output, format='JPEG', optimize=True, quality=quality)
            current_size = output.tell()
            
            if current_size <= IMAGE_TARGET_SIZE or quality <= IMAGE_QUALITY_MIN:
                break
            
            quality -= IMAGE_QUALITY_STEP
        
        # Save to temp folder
        temp_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        
        new_size = output.tell()
        reduction = ((original_size - new_size) / original_size) * 100 if original_size > 0 else 0
        
        return {
            'success': True,
            'original_name': original_filename,
            'new_name': new_filename,
            'safe_filename': safe_filename,
            'original_size': original_size,
            'new_size': new_size,
            'reduction': reduction,
            'width': img.width,
            'height': img.height
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'original_name': file.filename if file else 'unknown'
        }


def generate_explainer_prompt(topic, language):
    """
    Generate the prompt for Gemini AI to create lesson explainers.
    
    Args:
        topic (str): The lesson topic
        language (str): Target language
        
    Returns:
        str: Formatted prompt for AI
    """
    return f"""Generate exactly 5 simple, direct explainer texts for a {language} language learning lesson about "{topic}".

Each explainer should:
- Be very simple and straightforward (15-25 words maximum)
- Use plain, natural language like a friendly teacher
- Simply state what students will learn without exaggeration
- Examples: "Let's learn fruits in French", "Today we'll learn how to talk about colors in Spanish"

Keep it simple, clear, and natural. No fancy or over-enthusiastic language, explainer text should be in english strictly.

Format your response as a JSON array with exactly 5 options:
[
  "First explainer text here",
  "Second explainer text here",
  "Third explainer text here",
  "Fourth explainer text here",
  "Fifth explainer text here"
]

Return ONLY the JSON array, no other text."""


def parse_ai_response(response_text):
    """
    Parse AI response to extract JSON array of explainers.
    
    Handles various response formats including markdown code blocks.
    
    Args:
        response_text (str): Raw AI response
        
    Returns:
        list: List of explainer strings
        
    Raises:
        ValueError: If response cannot be parsed
    """
    json_match = response_text.strip()
    
    # Handle markdown code blocks
    if '```json' in response_text:
        json_match = response_text.split('```json')[1].split('```')[0].strip()
    elif '```' in response_text:
        json_match = response_text.split('```')[1].split('```')[0].strip()
    
    # Find JSON array
    start_idx = json_match.find('[')
    end_idx = json_match.rfind(']') + 1
    
    if start_idx == -1 or end_idx == 0:
        raise ValueError("No JSON array found in response")
    
    json_str = json_match[start_idx:end_idx]
    return json.loads(json_str)


def open_folder_in_explorer(folder_path):
    """
    Open a folder in the system file explorer.
    
    Works cross-platform (Windows, macOS, Linux).
    
    Args:
        folder_path (str): Path to folder
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    system = platform.system()
    try:
        if system == 'Windows':
            os.startfile(folder_path)
        elif system == 'Darwin':  # macOS
            subprocess.Popen(['open', folder_path])
        else:  # Linux
            subprocess.Popen(['xdg-open', folder_path])
        return True, None
    except Exception as e:
        return False, str(e)


# =============================================================================
# AUDIO GENERATOR ROUTES
# =============================================================================

@audio_bp.route('/generate', methods=['POST'])
def generate_audio():
    """
    Generate audio from text using ElevenLabs TTS.
    
    Expects JSON with 'text' and 'voice' fields.
    Text in { } is treated as native language.
    
    Returns:
        JSON response with generated audio file paths
    """
    try:
        data = request.json
        text = data.get('text', '').strip()
        selected_voice = data.get('voice', 'french')
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        if selected_voice not in VOICES:
            return jsonify({'success': False, 'error': 'Invalid voice selected'})
        
        voice_id = VOICES[selected_voice]['id']
        blocks = parse_text_blocks(text, selected_voice)
        
        if not blocks:
            return jsonify({'success': False, 'error': 'No valid text blocks found'})
        
        audio_folder = get_audio_folder()
        results = []
        
        for is_native, clean_text in blocks:
            if not clean_text:
                continue
            
            base_filename = text_to_filename(clean_text, selected_voice, is_native)
            filename = f"{base_filename}.mp3"
            output_path = audio_folder / filename
            
            success, error = text_to_speech(clean_text, output_path, voice_id)
            
            if success:
                results.append({
                    'filename': filename,
                    'path': f"/static/audio/{filename}",
                    'text': clean_text,
                    'language': selected_voice,
                    'is_native': is_native
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed for "{clean_text[:50]}...": {error}'
                })
            
            # Small delay between API calls
            time.sleep(0.2)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@audio_bp.route('/voices', methods=['GET'])
def get_voices():
    """
    Get list of available voices.
    
    Returns:
        JSON with voice names and IDs
    """
    return jsonify({
        'voices': {k: {'name': v['name']} for k, v in VOICES.items()}
    })


# =============================================================================
# EXPLAINER GENERATOR ROUTES
# =============================================================================

@explainer_bp.route('/generate', methods=['POST'])
def generate_explainers():
    """
    Generate lesson explainer options using Gemini AI.
    
    Expects JSON with 'topic' and 'language' fields.
    
    Returns:
        JSON with 5 explainer options
    """
    try:
        if not GEMINI_API_KEY:
            return jsonify({'error': 'Gemini API key not configured'}), 500
        
        data = request.json
        topic = data.get('topic', '')
        language = data.get('language', '')
        
        if not topic or not language:
            return jsonify({'error': 'Topic and language are required'}), 400
        
        # Generate prompt and call AI
        prompt = generate_explainer_prompt(topic, language)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        # Parse response
        explainers = parse_ai_response(response.text)
        
        if len(explainers) != 5:
            return jsonify({'error': 'Expected 5 explainers but got a different number'}), 500
        
        return jsonify({
            'success': True,
            'explainers': explainers,
            'topic': topic,
            'language': language
        })
        
    except Exception as e:
        print(f"Explainer generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@explainer_bp.route('/health', methods=['GET'])
def explainer_health():
    """
    Health check endpoint for explainer service.
    
    Returns:
        JSON with service status
    """
    return jsonify({
        'status': 'healthy',
        'api_configured': GEMINI_API_KEY is not None
    })


# =============================================================================
# IMAGE REDUCER ROUTES
# =============================================================================

@image_bp.route('/compress', methods=['POST'])
def compress():
    """
    Compress an uploaded image to ~500KB.
    
    Expects multipart form with 'image' file.
    
    Returns:
        JSON with compression results
    """
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        result = compress_image(file)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route('/download/<filename>')
def download(filename):
    """
    Download a compressed image.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        File download response
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename
            )
        
        # Try sanitized version
        safe_filename = sanitize_filename(filename)
        safe_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        if os.path.exists(safe_path):
            return send_file(
                safe_path,
                as_attachment=True,
                download_name=filename
            )
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@image_bp.route('/health', methods=['GET'])
def image_health():
    """
    Health check endpoint for image service.
    
    Returns:
        JSON with service status
    """
    return jsonify({'status': 'ok', 'upload_folder': UPLOAD_FOLDER})


# =============================================================================
# IMAGE RENAMER ROUTES
# =============================================================================

@renamer_bp.route('/rename', methods=['POST'])
def rename_images():
    """
    Rename and save uploaded images with custom names.
    
    Expects multipart form with 'names' (newline-separated) and 'images'.
    
    Returns:
        JSON with saved file information
    """
    names_raw = request.form.get('names', '')
    names = [n.strip() for n in names_raw.split('\n') if n.strip()]
    files = request.files.getlist('images')
    
    if not files or not names:
        return jsonify({'error': 'Please provide both images and names.'}), 400
    
    pairs = min(len(files), len(names))
    
    # Ensure output folder exists
    os.makedirs(DEFAULT_OUTPUT, exist_ok=True)
    
    saved_files = []
    for i in range(pairs):
        file = files[i]
        original_ext = os.path.splitext(file.filename)[1]
        new_name = names[i] + original_ext
        save_path = os.path.join(DEFAULT_OUTPUT, new_name)
        file.save(save_path)
        saved_files.append(new_name)
    
    return jsonify({
        'success': True,
        'count': len(saved_files),
        'folder': DEFAULT_OUTPUT,
        'files': saved_files
    })


@renamer_bp.route('/open-folder', methods=['POST'])
def open_folder():
    """
    Open the output folder in system file explorer.
    
    Returns:
        JSON with success status
    """
    folder = request.json.get('folder', DEFAULT_OUTPUT)
    
    if not os.path.isdir(folder):
        return jsonify({'error': 'Folder not found'}), 404
    
    success, error = open_folder_in_explorer(folder)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': error}), 500


@renamer_bp.route('/default-folder')
def get_default_folder():
    """
    Get the default output folder path.
    
    Returns:
        JSON with folder path
    """
    return jsonify({'folder': DEFAULT_OUTPUT})


# =============================================================================
# MAIN APPLICATION ROUTES
# =============================================================================

@app.route('/')
def dashboard():
    """
    Render the main dashboard page.
    
    Returns:
        Rendered HTML template
    """
    return render_template('dashboard.html')


@app.route('/health')
def health_check():
    """
    Overall application health check.
    
    Returns:
        JSON with all service statuses
    """
    return jsonify({
        'status': 'healthy',
        'services': {
            'audio': ELEVENLABS_API_KEY is not None,
            'explainer': GEMINI_API_KEY is not None,
            'image_reducer': True,
            'image_renamer': True
        }
    })


# =============================================================================
# REGISTER BLUEPRINTS
# =============================================================================

app.register_blueprint(audio_bp, url_prefix='/audio')
app.register_blueprint(explainer_bp, url_prefix='/explainer')
app.register_blueprint(image_bp, url_prefix='/image')
app.register_blueprint(renamer_bp, url_prefix='/renamer')


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    # Print startup banner
    print("\n" + "=" * 60)
    print("  CreatorHub - Content Tools Dashboard")
    print("=" * 60)
    print("\n  Tools Available:")
    print("    - Audio Generator    (ElevenLabs TTS)")
    print("    - Explainer Generator (Gemini AI)")
    print("    - Image Reducer      (Smart Compression)")
    print("    - Image Renamer      (Bulk Rename)")
    print("\n  API Status:")
    print(f"    - ElevenLabs: {'Configured' if ELEVENLABS_API_KEY else 'Not configured'}")
    print(f"    - Gemini:     {'Configured' if GEMINI_API_KEY else 'Not configured'}")
    print("\n  Open your browser and go to:")
    print("  http://localhost:5000")
    print("\n  Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")
    
    # Run the Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)
