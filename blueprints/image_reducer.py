"""
Image Reducer Blueprint
Smart Image Compression using PIL
"""

from flask import Blueprint, request, jsonify, send_file
from PIL import Image
import os
import io
import tempfile
import re

image_bp = Blueprint('image', __name__)

# Create a temporary directory for processing
UPLOAD_FOLDER = tempfile.mkdtemp()


def sanitize_filename(filename):
    name, ext = os.path.splitext(filename)
    safe_name = re.sub(r'[^\w\-_.]', '_', name)
    return f"{safe_name}{ext}"


def compress_image(file):
    try:
        img = Image.open(file)
        file.seek(0, 2)
        original_size = file.tell()
        file.seek(0)
        
        original_filename = file.filename
        name, ext = os.path.splitext(original_filename)
        new_filename = f"{name}1{ext}"
        
        safe_filename = sanitize_filename(new_filename)
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        max_dimension = 2000
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        target_size = 500 * 1024
        quality = 85
        step = 5
        
        output = io.BytesIO()
        
        while True:
            output.seek(0)
            output.truncate(0)
            
            img.save(output, format='JPEG', optimize=True, quality=quality)
            
            current_size = output.tell()
            
            if current_size <= target_size or quality <= 30:
                break
            
            quality -= step

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


@image_bp.route('/compress', methods=['POST'])
def compress():
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
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename
            )
        
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
def health():
    return jsonify({'status': 'ok', 'upload_folder': UPLOAD_FOLDER})
