import os
import subprocess
from flask import Flask, Response, send_file, abort

app = Flask(__name__)

# Paths to the media files
VIDEO_FILE = 'output.mjpeg'
AUDIO_FILE = 'output.mp3'
INPUT_FILE = 'input.mp4'
CHUNK_SIZE = 12345678  # Size of chunks in bytes suitable for the microcontroller

def convert_media():
    # Check if output files already exist to avoid redundant conversion
    if not os.path.exists(VIDEO_FILE) or not os.path.exists(AUDIO_FILE):
        # Convert audio
        subprocess.run([
            "ffmpeg", "-i", INPUT_FILE, "-ar", "44100", "-ac", "1", "-q:a", "9", AUDIO_FILE
        ], check=True)

        # Convert video
        subprocess.run([
            "ffmpeg", "-i", INPUT_FILE, "-vf", "fps=24,scale=160:128:flags=lanczos", "-q:v", "9", VIDEO_FILE
        ], check=True)

@app.route('/video')
def video():
    def generate():
        try:
            with open(VIDEO_FILE, 'rb') as video_file:
                while True:
                    chunk = video_file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        except FileNotFoundError:
            abort(404)

    return Response(generate(), mimetype='video/mjpeg')

@app.route('/audio')
def audio():
    def generate():
        try:
            with open(AUDIO_FILE, 'rb') as audio_file:
                while True:
                    chunk = audio_file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        except FileNotFoundError:
            abort(404)

    return Response(generate(), mimetype='audio/mpeg')

if __name__ == '__main__':
    convert_media()
    app.run(host='0.0.0.0', port=5000, debug=True)
