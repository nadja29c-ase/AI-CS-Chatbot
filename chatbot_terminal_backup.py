from openai import OpenAI
from dotenv import load_dotenv
import os


# Functions definitions

'''
def test_environment_setup() -> bool:
    """Test if all required packages are properly installed and configured."""
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        import os
        
        # Test environment variables
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
    

        if not api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False
            
        print("✅ All packages imported successfully")
        print("✅ Environment variables loaded")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
'''


#Enable requests to OpenAI's API.

def prompt_system():
    with open("sys_prompt.txt", "r") as file:
        system_prompt = file.read().strip()
    return system_prompt


def create_openai_connector():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    return client

#Create a multi-turn question-response conversation with OpenAI's API and save the conversation history.

def send_request_to_openai(client, system_prompt):
    messages = [ {"role": "system", "content": system_prompt},
        ]
    
    while True:
        user_q = input("User: ")
        user_q_dict = {"role": "user", "content": user_q}
        messages.append(user_q_dict)
        
        if user_q.lower() == "close":
            print("Conversation closed.")
            break
        else:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=messages,
                max_completion_tokens = 50,
                temperature=0.7,
            )
            print("Assistant:", response.choices[0].message.content)
            assistant_dict = {"role": "assistant", "content": response.choices[0].message.content}
            messages.append(assistant_dict)

    return messages


def main():
    send_request_to_openai(
        client=create_openai_connector(),
        system_prompt=prompt_system()
    )
    

if __name__ == "__main__":
    #test_environment_setup()
    main()





    
