import requests
import json
import sys

URL = "http://localhost:8001/chat"

def chat():
    print("Welcome to DeepAgents Chat! Type 'exit' or 'quit' to stop.")
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            payload = {
                "messages": [{"role": "user", "content": user_input}]
            }
            
            response = requests.post(URL, json=payload)
            response.raise_for_status()
            
            data = response.json()
            print(f"Agent: {data.get('content')}")
            
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to the server using URL:", URL)
            print("Is the server running? (Run 'uvicorn main:app --port 8001')")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    chat()
