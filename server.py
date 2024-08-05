import os
import subprocess
import yt_dlp
from flask import Flask, Response, render_template, request, redirect, url_for, abort

app = Flask(__name__)

CHUNK_SIZE = 987546775  # Size of chunks in bytes suitable for the microcontroller

# Define paths for the media files
VIDEO_FILE = 'output.mjpeg'
AUDIO_FILE = 'output.mp3'
VIDEO_INPUT_FILE = 'input.mp4'

@app.route('/')
def home():
    return render_template('index.html')  # Create an index.html file with a search bar

@app.route('/search', methods=['POST'])
def search():
    # Remove previously downloaded files
    if os.path.exists(VIDEO_INPUT_FILE):
        os.remove(VIDEO_INPUT_FILE)
    if os.path.exists(VIDEO_FILE):
        os.remove(VIDEO_FILE)
    if os.path.exists(AUDIO_FILE):
        os.remove(AUDIO_FILE)

    query = request.form['query']
    search_results = yt_dlp.YoutubeDL().extract_info(f"ytsearch5:{query}", download=False)['entries']
    return render_template('results.html', results=search_results)  # Create a results.html file to display search results

@app.route('/download/<video_id>')
def download(video_id):
    ydl_opts = {
        'format': 'worst',  # Download in low quality
        'outtmpl': VIDEO_INPUT_FILE,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

    if not os.path.exists(VIDEO_INPUT_FILE):
        return "Error: Failed to download video."

    # Convert audio
    try:
        subprocess.run([
            "ffmpeg", "-i", VIDEO_INPUT_FILE, "-ar", "44100", "-ac", "1", "-q:a", "9", AUDIO_FILE
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg error: {e.stderr.decode()}")
        return "Error: Failed to convert audio."

    # Convert video to MJPEG
    try:
        subprocess.run([
            "ffmpeg", "-i", VIDEO_INPUT_FILE, "-vf", "fps=24,scale=160:128:flags=lanczos", "-q:v", "9", VIDEO_FILE
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg error: {e.stderr.decode()}")
        return "Error: Failed to convert video."

    return redirect(url_for('serve'))

@app.route('/serve')
def serve():
    return render_template('serve.html')  # Create a serve.html file to provide links to download/stream the video and audio

@app.route('/video')
def video():
    def generate():
        try:
            with open(VIDEO_FILE, 'rb') as video_file:
                while chunk := video_file.read(CHUNK_SIZE):
                    yield chunk
        except FileNotFoundError:
            abort(404)

    return Response(generate(), mimetype='video/mjpeg')

@app.route('/audio')
def audio():
    def generate():
        try:
            with open(AUDIO_FILE, 'rb') as audio_file:
                while chunk := audio_file.read(CHUNK_SIZE):
                    yield chunk
        except FileNotFoundError:
            abort(404)

    return Response(generate(), mimetype='audio/mpeg')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
