import openai
from django.shortcuts import render
from django.http import JsonResponse
import threading

OPENAI_API_KEY = 'your_open_ai_key'
openai.api_key = OPENAI_API_KEY

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
        api_thread = threading.Thread(target=call_openai_api, args=(prompt, response_list))
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