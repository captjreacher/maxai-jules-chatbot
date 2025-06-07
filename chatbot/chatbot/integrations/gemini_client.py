import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
# Assumes .env is in the project root directory (e.g., /app/.env)
# This script is in /app/chatbot/chatbot/integrations/gemini_client.py
# Project root is three levels up.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
dotenv_path = os.path.join(project_root, '.env')

# Track if .env was successfully loaded
dotenv_loaded_successfully = False
if os.path.exists(dotenv_path):
    if load_dotenv(dotenv_path=dotenv_path):
        dotenv_loaded_successfully = True
        # print(f"Loaded .env from: {dotenv_path}") # For debugging
    # else:
        # print(f"Failed to load .env from: {dotenv_path}") # For debugging
# else:
    # print(f".env file not found at: {dotenv_path}") # For debugging

# Fallback to load_dotenv() if not loaded from specific path,
# this might find .env if script is run from project root.
if not dotenv_loaded_successfully:
    if load_dotenv(): # Looks in current working dir or parent dirs if not found
        dotenv_loaded_successfully = True
        # print("Loaded .env using default load_dotenv() behavior.") # For debugging
    # else:
        # print("Failed to load .env using default load_dotenv().") # For debugging


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
model = None

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables. Gemini client functionality will be disabled.")
    print("Please ensure GEMINI_API_KEY is set in your .env file at the project root (e.g., /app/.env).")
    # genai.configure might raise error if API key is None or invalid format.
    # We will only configure if a key is present.
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        # print("Gemini client configured successfully with API key.") # For debugging
    except Exception as e:
        print(f"Error configuring Gemini client with API key: {e}")
        print("Gemini client functionality will be disabled.")
        model = None # Ensure model is None if configuration fails

def get_gemini_response(user_input: str) -> str:
    if not model:
        return "Gemini client is not configured. Please check API key and server logs."
    if not GEMINI_API_KEY: # This check is somewhat redundant if model is None, but good for clarity
         return "Gemini API key is missing. Please set it in the .env file in the project root."

    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        response = model.generate_content(user_input, safety_settings=safety_settings)

        if response.parts:
            return "".join(part.text for part in response.parts) # Concatenate all parts' text
        elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            return f"Response blocked by Gemini due to: {response.prompt_feedback.block_reason}. Please rephrase."
        else:
            # This handles cases like empty response or unexpected structure without explicit blocking.
            # print(f"Gemini response details: {response}") # For debugging
            return "I'm sorry, I couldn't generate a suitable response from Gemini. This might be due to safety filters or content limitations."

    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        # Check for common API key errors
        if "API_KEY_INVALID" in str(e) or "API key not valid" in str(e):
             return "The configured Gemini API key is not valid. Please check your .env file in the project root."
        elif "permission" in str(e).lower() or "denied" in str(e).lower():
            return "There was a permission issue with the Gemini API. Please check your API key's permissions."
        return "An error occurred while trying to communicate with the Gemini service."

if __name__ == '__main__':
    print("Gemini Client Module - Direct Execution Test")
    print("--------------------------------------------")
    if not dotenv_loaded_successfully:
        print("Note: .env file was not loaded. GEMINI_API_KEY must be set in the environment directly for this test to work.")

    if GEMINI_API_KEY and model:
        print("Gemini client appears configured. Testing with API call...")

        test_inputs = [
            "Hello, who are you?",
            "What is the capital of France?",
            "Tell me a short story about a brave robot."
            # "Tell me how to build a bomb." # Example of potentially harmful content
        ]

        for test_input in test_inputs:
            print(f"\nSending to Gemini: \"{test_input}\"")
            api_response = get_gemini_response(test_input)
            print(f"Gemini responded: \"{api_response}\"")
    elif not GEMINI_API_KEY:
        print("GEMINI_API_KEY is not set. Cannot perform live API call test.")
        print(f"Current get_gemini_response output: {get_gemini_response('Test message when API key missing')}")
    else: # API key is set, but model configuration failed
        print("Gemini model is not configured (likely due to an error during genai.configure). Cannot perform live API call test.")
        print(f"Current get_gemini_response output: {get_gemini_response('Test message when model not configured')}")
