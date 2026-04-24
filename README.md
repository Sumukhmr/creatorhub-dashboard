# 🌐 LingoTran Tools Dashboard

A unified Flask dashboard combining multiple content creation tools for language learning platforms.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Tools Included

| Tool | Description | API Required |
|------|-------------|--------------|
| 🎙️ **Audio Generator** | Multi-language TTS using ElevenLabs | ElevenLabs |
| 📝 **Explainer Generator** | AI-powered lesson introductions | Google Gemini |
| 🖼️ **Image Reducer** | Smart image compression to ~500KB | None |
| ✏️ **Image Renamer** | Bulk rename images with custom names | None |

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/lingotran-dashboard.git
cd lingotran-dashboard
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run the application

```bash
python app.py
```

Open your browser and go to: **http://localhost:5000**

## 🗂️ Project Structure

```
lingotran-dashboard/
├── app.py                      # Main Flask app
├── blueprints/
│   ├── __init__.py
│   ├── audio_generator.py      # Audio TTS blueprint
│   ├── explainer_generator.py  # AI explainer blueprint
│   ├── image_reducer.py        # Image compression blueprint
│   └── image_renamer.py        # Bulk rename blueprint
├── templates/
│   └── dashboard.html          # Main dashboard UI
├── static/
│   └── audio/                  # Generated audio files
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 📚 API Endpoints

### Audio Generator
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/audio/generate` | Generate audio from text |
| GET | `/audio/voices` | Get available voices |

### Explainer Generator
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/explainer/generate` | Generate 5 explainer options |
| GET | `/explainer/health` | Health check |

### Image Reducer
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/image/compress` | Compress an image |
| GET | `/image/download/<filename>` | Download compressed image |
| GET | `/image/health` | Health check |

### Image Renamer
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/renamer/rename` | Rename and save images |
| POST | `/renamer/open-folder` | Open output folder |
| GET | `/renamer/default-folder` | Get default output path |

## 🔑 API Keys

### ElevenLabs (Audio Generator)
Get your API key from: [https://elevenlabs.io/](https://elevenlabs.io/)

### Google Gemini (Explainer Generator)
Get your API key from: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

## 🎨 Screenshots

The dashboard features a modern, responsive design with:
- Tab-based navigation
- Tool cards on the home screen
- Drag & drop file uploads
- Real-time preview
- Progress indicators

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
