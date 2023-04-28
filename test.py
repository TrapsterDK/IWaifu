import openai

openai.api_key = "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"

messages = []
content = input("User: ")
messages.append({"role": "user", "content": content})

completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)

chat_response = completion.choices[0].message.content
print(f"ChatGPT: {chat_response}")
