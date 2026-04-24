"""
Image Renamer Blueprint
Bulk Image Renaming Tool
"""

from flask import Blueprint, request, jsonify
import os
import platform
import subprocess

renamer_bp = Blueprint('renamer', __name__)

# Default output folder
DEFAULT_OUTPUT = os.path.join(os.path.expanduser('~'), 'Downloads', 'renamed_images')


@renamer_bp.route('/rename', methods=['POST'])
def rename_images():
    names_raw = request.form.get('names', '')
    names = [n.strip() for n in names_raw.split('\n') if n.strip()]
    files = request.files.getlist('images')

    if not files or not names:
        return jsonify({'error': 'Please provide both images and names.'}), 400

    pairs = min(len(files), len(names))

    output_folder = DEFAULT_OUTPUT
    os.makedirs(output_folder, exist_ok=True)

    saved_files = []
    for i in range(pairs):
        file = files[i]
        original_ext = os.path.splitext(file.filename)[1]
        new_name = names[i] + original_ext
        save_path = os.path.join(output_folder, new_name)
        file.save(save_path)
        saved_files.append(new_name)

    return jsonify({
        'success': True,
        'count': len(saved_files),
        'folder': output_folder,
        'files': saved_files
    })


@renamer_bp.route('/open-folder', methods=['POST'])
def open_folder():
    folder = request.json.get('folder', DEFAULT_OUTPUT)
    if not os.path.isdir(folder):
        return jsonify({'error': 'Folder not found'}), 404

    system = platform.system()
    try:
        if system == 'Windows':
            os.startfile(folder)
        elif system == 'Darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@renamer_bp.route('/default-folder')
def get_default_folder():
    return jsonify({'folder': DEFAULT_OUTPUT})
