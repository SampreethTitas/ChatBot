import openai
from config import Config
openai.api_key = Config.OPENAI_API_KEY

def get_chat_response(user_message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ]
    )
    return response["choices"][0]["message"]["content"]