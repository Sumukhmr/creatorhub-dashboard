"""
Explainer Generator Blueprint
AI-Powered Lesson Introductions using Gemini AI
"""

from flask import Blueprint, request, jsonify
import google.generativeai as genai
import json
import os

explainer_bp = Blueprint('explainer', __name__)

# Gemini API configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@explainer_bp.route('/generate', methods=['POST'])
def generate_explainers():
    try:
        if not GEMINI_API_KEY:
            return jsonify({'error': 'Gemini API key not configured'}), 500
        
        data = request.json
        topic = data.get('topic', '')
        language = data.get('language', '')
        
        if not topic or not language:
            return jsonify({'error': 'Topic and language are required'}), 400
        
        prompt = f"""Generate exactly 5 simple, direct explainer texts for a {language} language learning lesson about "{topic}".

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

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        response_text = response.text.strip()
        
        json_match = response_text
        if '```json' in response_text:
            json_match = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            json_match = response_text.split('```')[1].split('```')[0].strip()
        
        start_idx = json_match.find('[')
        end_idx = json_match.rfind(']') + 1
        
        if start_idx == -1 or end_idx == 0:
            return jsonify({'error': 'Invalid response format from AI'}), 500
            
        json_str = json_match[start_idx:end_idx]
        explainers = json.loads(json_str)
        
        if len(explainers) != 5:
            return jsonify({'error': 'Expected 5 explainers but got a different number'}), 500
        
        return jsonify({
            'success': True,
            'explainers': explainers,
            'topic': topic,
            'language': language
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@explainer_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'api_configured': GEMINI_API_KEY is not None
    })
