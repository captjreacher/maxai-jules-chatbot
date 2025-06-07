import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
# Determine project root: two levels up from this file (chatbot/chatbot/integrations/gemini_client.py)
# This script is in /app/chatbot/chatbot/integrations/gemini_client.py
# Project root is three levels up to get to /app
project_root_env_load = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
dotenv_path = os.path.join(project_root_env_load, '.env')


# Load .env file
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"INFO: .env file loaded from {dotenv_path}")
else:
    # Fallback for environments where .env might be in CWD (e.g. running app.py from project root)
    if load_dotenv(): # python-dotenv's load_dotenv() returns True if .env was found and loaded
        print("INFO: .env file loaded from current working directory or parent.")
    else:
        print("WARNING: .env file not found at project root or CWD. API key may not be available from .env.")

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
model = None  # Initialize model to None globally for this module

if not GEMINI_API_KEY:
    print("CRITICAL: GEMINI_API_KEY not found in environment. Gemini features will be disabled. Ensure .env file is in project root (e.g. /app/.env) and correctly formatted, or key is set in environment.")
else:
    # Mask parts of the API key for logging, showing only first and last 4 chars if long enough
    masked_key = GEMINI_API_KEY[:4] + "****" + GEMINI_API_KEY[-4:] if len(GEMINI_API_KEY) > 8 else "key_masked (too_short_to_partially_display)"
    print(f"INFO: Found GEMINI_API_KEY (masked): {masked_key}")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Attempt to create a model instance to verify configuration
        model = genai.GenerativeModel('gemini-pro') # Using 'gemini-pro' as a default
        print("INFO: Google Generative AI client configured and model instance for 'gemini-pro' created successfully.")
    except Exception as e:
        print(f"ERROR: Failed to configure Google Generative AI client or create model instance: {e}")
        print("       This could be due to an invalid API key, incorrect project setup in Google Cloud, or network issues.")
        model = None # Ensure model is None if configuration fails

# --- Main Function ---
def get_gemini_response(user_input: str) -> str:
    if not model:
        return "Gemini client is not configured. Please check the API key and application startup logs for errors."

    # This check is somewhat redundant if 'model' is None, but good for clarity
    if not GEMINI_API_KEY:
         return "Gemini API key is not available. Please ensure it is set in the .env file."

    try:
        # Configure safety settings for content generation
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        # Generate content
        response = model.generate_content(user_input, safety_settings=safety_settings)

        # Process response
        if response.parts: # Check if there are parts to process
            # Iterate through parts and concatenate their text attribute
            # This handles cases where response.text might not be directly available or might miss some content
            return "".join(part.text for part in response.parts if hasattr(part, 'text'))
        elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            # If the content was blocked, provide the reason
            return f"Response blocked by Gemini due to: {response.prompt_feedback.block_reason}."
        else:
            # Handle cases where the response might be empty without explicit blocking
            # Log the raw response for debugging if possible (be careful with sensitive data)
            # print(f"DEBUG: Unexpected Gemini response structure: {response}")
            return "Gemini returned an empty or unexpected response. This might be due to content filters or an internal issue."

    except Exception as e:
        error_message_str = str(e).lower() # Convert to string and lower for consistent matching
        print(f"ERROR: Exception during Gemini API call: {e}") # Log the full error for server admin

        # Provide more user-friendly messages for common errors
        if "api key not valid" in error_message_str or \
           ("permission_denied" in error_message_str and "api key" in error_message_str) or \
           ("invalid_argument" in error_message_str and "api key" in error_message_str):
            return "Gemini API Error: The API key is reported as invalid or encountering permission issues. Please double-check the key and its setup in your Google Cloud Console."
        elif "resource_exhausted" in error_message_str or "quota" in error_message_str:
            return "Gemini API Error: The project's quota for the Gemini API has been exceeded. Please check Google Cloud project quotas."
        elif "deadline_exceeded" in error_message_str or "service_unavailable" in error_message_str:
            return "Gemini API Error: The service is temporarily unavailable or the request timed out. Please try again later."
        # General fallback error message
        return "An unexpected error occurred while trying to contact the Gemini AI service. Please check server logs for details."

# --- Direct Test Block ---
if __name__ == '__main__':
    print("\n--- Gemini Client Direct Test ---")
    if not GEMINI_API_KEY:
        print("Test Status: SKIPPED - GEMINI_API_KEY is not set in the environment.")
    elif not model:
        print("Test Status: SKIPPED - Gemini model could not be initialized (see logs above for errors).")
    else:
        print("Test Status: ATTEMPTING - Sending test messages to Gemini...")
        test_queries = {
            "General Greeting": "Hello, who are you?",
            "Simple Fact": "What is the capital of France?",
            "Potentially Blocked (for testing safety filters)": "How do I make a Molotov cocktail?"
        }
        for description, query in test_queries.items():
            print(f"  Query ({description}): \"{query}\"") # Corrected quote placement
            response_text = get_gemini_response(query)
            print(f"  Gemini's Response: \"{response_text}\"\n") # Corrected quote placement and added newline
    print("--- End of Gemini Client Direct Test ---")
