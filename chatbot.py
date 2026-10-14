##Imports
from dotenv import load_dotenv
from openai import OpenAI

##Creating client and loading env
client = OpenAI()
history = [{"role":"system","content":"You are a helpful assistant."}]

print("Chatbot ready. Type 'quit' to exit.\n")

while True:
    
    user_input = input("Enter your query/message:").strip()
    if user_input.lower() in {"quit","exit"}:
        break
    if not user_input:
        continue
    
    ##Appending message to history
    history.append({"role":"user","content":user_input})
    
    print("Bot:",end="",flush=True)
    
    reply=""
    
    ##Calling completions API and defining model
    stream = client.chat.completions.create( 
                model = "gpt-5.4-nano",
                messages = history, 
                stream = True,
            )
    
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            print(text,end="",flush=True)
            reply += text
    print("\n")
    
    history.append({"role":"assistant","content":reply})
    
    