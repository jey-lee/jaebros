import openai
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import threading
import os
import requests
from google.cloud import storage
from datetime import datetime



openai.api_key = settings.OPENAI_KEY
client = openai

leap_assistant = client.beta.assistants.retrieve("asst_pr7frjRKV8gKLStqf7r9EkHK")
thread = client.beta.threads.create()

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

        print(message_chat)

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
        print(mode)
        if mode == 'audio':
            audio_url = get_tts_audio(response)
        else:
            audio_url = ''
        print(audio_url)

        return JsonResponse({
            'message': message_chat, 
            'response': response,
            'audio_url': str(audio_url),
            })
    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_tts_audio(text):
    # Initialize a Cloud Storage client
    storage_client = storage.Client()
    bucket = storage_client.bucket('jaebros.appspot.com')
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S") 


    speech_file_path = Path(__file__).parent / "static" / "audio" / "speech.mp3"

    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        speed= 1.1,
        input=text
    )

    # Get audio content as bytes
    audio_content = response.content
    #filename = "speech.mp3"+timestamp
    filename = f"speech-{timestamp}.mp3" 

    blob = bucket.blob(filename)

    # Delete the existing blob if it exists
    if blob.exists():
        blob.delete()

    # Upload speech to Cloud Storage
    blob.upload_from_string(audio_content, content_type="audio/mpeg")

    # Make file public (optional)
    blob.make_public()

    # response.stream_to_file(speech_file_path)
    return blob.public_url 