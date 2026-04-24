"""
LingoTran Tools Dashboard
=========================
A unified Flask dashboard combining multiple content creation tools:
- Audio Generator (ElevenLabs TTS)
- Explainer Generator (Gemini AI)
- Image Reducer (Smart Compression)
- Image Renamer (Bulk Rename)
"""

from flask import Flask, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import blueprints
from blueprints.audio_generator import audio_bp
from blueprints.explainer_generator import explainer_bp
from blueprints.image_reducer import image_bp
from blueprints.image_renamer import renamer_bp

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Register blueprints
app.register_blueprint(audio_bp, url_prefix='/audio')
app.register_blueprint(explainer_bp, url_prefix='/explainer')
app.register_blueprint(image_bp, url_prefix='/image')
app.register_blueprint(renamer_bp, url_prefix='/renamer')


@app.route('/')
def dashboard():
    return render_template('dashboard.html')


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  LingoTran Tools Dashboard")
    print("=" * 60)
    print("\n  Tools Available:")
    print("    - Audio Generator    (ElevenLabs TTS)")
    print("    - Explainer Generator (Gemini AI)")
    print("    - Image Reducer      (Smart Compression)")
    print("    - Image Renamer      (Bulk Rename)")
    print("\n  Open your browser and go to:")
    print("  http://localhost:5000")
    print("\n  Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

