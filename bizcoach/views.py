import openai
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import threading

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

        return JsonResponse({'message': message_chat, 'response': response})
    return JsonResponse({'error': 'Invalid request'}, status=400)