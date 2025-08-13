import requests

def send_message(message):
    response = requests.post('http://127.0.0.1:5000/chat', 
                            json={'message': message})
    print(f"You: {message}")
    print(f"AI: {response.text}")
    print("-" * 50)

# Test conversation memory
print("Testing conversation memory...")
print("=" * 50)

send_message("Hello, my name is Sarah")
send_message("What's my name?")
send_message("What did we talk about so far?")