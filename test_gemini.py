import google.generativeai as genai
import sys

API_KEY = "AIzaSyBnPyh-o5Z9cefQXACJhWD1EY6rdwcWVpA" # Reverting to original key from earlier to test
API_KEY2 = "AIzaSyA99xVLS2m9enXhXnYCYmFhjCUizmDY4GE" # The newer key

def test_key(key, name):
    print(f"\n--- Testing {name} ---")
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'hello world' in one sentence.")
        print("Success! Response:")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

test_key(API_KEY, "Original Key")
test_key(API_KEY2, "New Key")
