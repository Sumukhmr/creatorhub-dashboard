"""
Audio Generator Blueprint
Multi-Language TTS using ElevenLabs API
"""

from flask import Blueprint, request, jsonify
import requests
from pathlib import Path
import time
import os

audio_bp = Blueprint('audio', __name__)

# ElevenLabs API configuration
API_KEY = os.getenv('ELEVENLABS_API_KEY')

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

MODEL_ID = "eleven_v3"


def get_audio_folder():
    audio_folder = Path(__file__).parent.parent.resolve() / "static" / "audio"
    audio_folder.mkdir(parents=True, exist_ok=True)
    return audio_folder


def parse_text_blocks(text, selected_voice):
    blocks = []
    i = 0
    
    while i < len(text):
        while i < len(text) and text[i] in ' \t':
            i += 1
        
        if i >= len(text):
            break
            
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
        
        elif text[i] == '\n':
            i += 1
            continue
        
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
    words = text.strip().replace('\n', ' ').split()[:10]
    filename = "_".join(words)
    filename = filename.lower()
    filename = "".join(c if c.isalnum() or c == "_" else "_" for c in filename)
    filename = "_".join(filter(None, filename.split("_")))
    
    if is_native:
        suffix = VOICES[selected_voice]['native_suffix']
    else:
        suffix = VOICES[selected_voice]['english_suffix']
    
    return filename + suffix


def text_to_speech(text, output_path, voice_id):
    if not API_KEY:
        return False, "API key not configured"
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": API_KEY
    }
    
    data = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 1.0,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
            "speed": 1.0
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True, None
    else:
        return False, f"Error {response.status_code}: {response.text}"


@audio_bp.route('/generate', methods=['POST'])
def generate():
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
    return jsonify({
        'voices': {k: {'name': v['name']} for k, v in VOICES.items()}
    })
