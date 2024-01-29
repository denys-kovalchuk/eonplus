import os
from openai import OpenAI
from dotenv import load_dotenv


def openai_request(input_text: dict[str: str]) -> str:
    """Makes a request to OpenAI's Chat API to summarize the given input text."""
    load_dotenv()
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"Summarize the following input {input_text}",
            }
        ],
        model="gpt-3.5-turbo",
    )
    return chat_completion['choices'][0]['message']['content']
