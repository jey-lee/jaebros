import openai
from pathlib import Path

from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import whisper
import logging
import threading
import os
import subprocess
import requests



openai.api_key = settings.OPENAI_KEY
client = openai

leap_assistant = client.beta.assistants.retrieve("asst_pr7frjRKV8gKLStqf7r9EkHK")
thread = client.beta.threads.create()

# Set the full path to ffmpeg
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

# Load the Whisper model
model = whisper.load_model("base")

# Set up logging
logger = logging.getLogger(__name__)

# Function to call the OpenAI API
def call_openai_api_assistant(prompt, response_list):
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )
    try:
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=leap_assistant.id,
            )
        if run.status == 'completed': 
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            last_message = messages.data[0].content[0].text.value

        else:
            print('### status : ' + run.status)
        
        response_list.append(last_message)
    except Exception as e:
        response_list.append(f"Error: {e}")

# Function to call the OpenAI API
def call_openai_api(prompt, response_list):
    print('### Prompt : ' + prompt)
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a biz coach. keep your response short to one or two sentence and follow up with a question"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
        )
        result = response.choices[0].message.content
        print(result)
        response_list.append(result)
    except Exception as e:
        response_list.append(f"Error: {e}")

def index(request):
    return render(request, 'bizcoach/index.html')

def send_message(request):
    if request.method == 'POST':
        message_chat = request.POST.get('message', '')
        mode = request.POST.get('mode', '')

        prompt = message_chat
        response_list = []

        # Create and start a thread
        api_thread = threading.Thread(target=call_openai_api_assistant, args=(prompt, response_list))
        api_thread.start()

        # Wait for the thread to complete
        api_thread.join()

        # Get the result from the response list
        if response_list:
            result = response_list[0]
        else:
            result = "No response received."

        response = result

        # Call OpenAI TTS API
        if mode == 'audio':
            audio_url = get_tts_audio(response)
        else:
            audio_url = ''

        return JsonResponse({
            'message': message_chat, 
            'response': response,
            'audio_url': str(audio_url),
            })
    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_tts_audio(text):
    speech_file_path = Path(__file__).parent / "static" / "audio" / "speech.mp3"

    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        speed= 1.1,
        input=text
    )
    response.stream_to_file(speech_file_path)
    return os.path.join('/static/audio/speech.mp3')

@csrf_exempt
def transcribe(request):
    if request.method == 'POST' and request.FILES['audio']:
        try:
            audio_file = request.FILES['audio']
            file_name = default_storage.save(audio_file.name, audio_file)
            file_path = default_storage.path(file_name)

            print(file_name + "/" + file_path)

            # Log the MIME type, file extension, and file size
            mime_type = audio_file.content_type
            file_extension = os.path.splitext(file_name)[1]
            file_size = audio_file.size
            logger.info(f"Received audio file with MIME type: {mime_type}, extension: {file_extension}, size: {file_size} bytes")

            # Print the first few bytes of the file for debugging
            with open(file_path, 'rb') as f:
                file_head = f.read(100)
                logger.info(f"File head: {file_head}")

            # Log additional debug info
            logger.debug(f"File path: {file_path}")
            wav_file_path = file_path + '.wav'
            command = f"ffmpeg -i {file_path} -ac 1 -ar 16000 -f wav {wav_file_path}"
            logger.debug(f"Running command: {command}")

            # Run ffmpeg command and log output
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            logger.debug(f"ffmpeg stdout: {result.stdout}")
            logger.debug(f"ffmpeg stderr: {result.stderr}")

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command)

            # Check if the WAV file was created successfully
            if not os.path.exists(wav_file_path):
                raise FileNotFoundError(f"WAV file was not created: {wav_file_path}")

            # Transcribe audio using Whisper
            result = model.transcribe(wav_file_path)
            transcription = result['text']
            print (transcription)

            # Clean up the stored files
            default_storage.delete(file_name)
            if os.path.exists(wav_file_path):
                os.remove(wav_file_path)

            return JsonResponse({'transcription': transcription})
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr}")
            return JsonResponse({'error': f"ffmpeg error: {e.stderr}"}, status=500)
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)