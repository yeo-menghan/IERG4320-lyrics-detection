import os
from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from google.cloud import speech
from pydub.utils import mediainfo

app = Flask(__name__)

# Set up Google Cloud credentials
client_file = "google-speech.json"
credentials = service_account.Credentials.from_service_account_file(client_file)

# Create the uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # This ensures the 'uploads' directory exists

def transcribe_file(audio_file: str) -> str:
    """Transcribe the given audio file."""
    client = speech.SpeechClient(credentials=credentials)

    with open(audio_file, "rb") as f:
        audio_content = f.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        sample_rate_hertz=44100,
        language_code="en-US",
    )

    response = client.recognize(config=config, audio=audio)

    # Get the transcript from the first result (most likely alternative)
    if response.results:
        return response.results[0].alternatives[0].transcript
    else:
        return "No speech detected."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Check if the file is part of the request
        if 'file' not in request.files:
            return jsonify({"error": "No file part"})

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"})

        # Ensure the file is an MP3 and its length is under 1 minute
        if file and file.filename.endswith('.mp3'):
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)

            # Check file duration (ensure it's less than 1 minute)
            info = mediainfo(file_path)
            duration = float(info['duration'])

            if duration > 60:
                os.remove(file_path)
                return jsonify({"error": "File is too long. Must be under 1 minute."})

            # Transcribe the audio
            transcript = transcribe_file(file_path)

            # Clean up the uploaded file after processing
            os.remove(file_path)

            return jsonify({"transcription": transcript})

        return jsonify({"error": "Invalid file format. Only MP3 allowed."})

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)
