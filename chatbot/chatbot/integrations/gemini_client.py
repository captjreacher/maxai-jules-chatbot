import os
import google.generativeai as genai
from dotenv import load_dotenv # Ensure this is at the top

# --- Configuration & Initial Logging ---
# Determine project root: This file is in chatbot/chatbot/integrations/
# Project root is three levels up.
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')

print(f"DEBUG (gemini_client.py): Calculated PROJECT_ROOT_DIR: {PROJECT_ROOT_DIR}")
print(f"DEBUG (gemini_client.py): Calculated DOTENV_PATH: {DOTENV_PATH}")

if os.path.exists(DOTENV_PATH):
    dotenv_loaded = load_dotenv(dotenv_path=DOTENV_PATH)
    print(f"DEBUG (gemini_client.py): Attempted to load .env from {DOTENV_PATH}. Success: {dotenv_loaded}")
else:
    print(f"DEBUG (gemini_client.py): .env file not found at {DOTENV_PATH}. Attempting to load from CWD or other dotenv search paths.")
    # load_dotenv() searches CWD and parent directories if path_override is not given
    dotenv_loaded_fallback = load_dotenv()
    print(f"DEBUG (gemini_client.py): Attempted to load .env via default search. Success: {dotenv_loaded_fallback}")
    if not dotenv_loaded_fallback:
        print("WARNING (gemini_client.py): .env file not found at project root or via default search.")

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# Per previous steps, CHOSEN_MODEL_NAME was updated to 'models/gemini-1.5-flash-latest'
CHOSEN_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'models/gemini-1.5-flash-latest')
model_instance = None

# Log values immediately after trying to get them from environment
print(f"DEBUG (gemini_client.py): GEMINI_API_KEY loaded: {'******' + GEMINI_API_KEY[-4:] if GEMINI_API_KEY and len(GEMINI_API_KEY) > 4 else 'Not found or too short'}")
print(f"DEBUG (gemini_client.py): CHOSEN_MODEL_NAME (from env or default): {CHOSEN_MODEL_NAME}")

if not GEMINI_API_KEY:
    print("CRITICAL (gemini_client.py): GEMINI_API_KEY is NOT FOUND in environment. Gemini features will be disabled.")
elif not CHOSEN_MODEL_NAME:
    print("CRITICAL (gemini_client.py): CHOSEN_MODEL_NAME is NOT SET (should have a default). Gemini features will be disabled.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model_instance = genai.GenerativeModel(CHOSEN_MODEL_NAME)
        print(f"INFO (gemini_client.py): Google Generative AI client configured. Model to use: '{CHOSEN_MODEL_NAME}'. Instance created: {model_instance is not None}")
    except Exception as e:
        print(f"ERROR (gemini_client.py): Failed to configure Google API client or initialize model '{CHOSEN_MODEL_NAME}': {e}")
        model_instance = None

# --- Utility Function to List Models (kept for direct testing/diag) ---
def list_available_models_for_api_key():
    if not GEMINI_API_KEY:
        print("ERROR (list_models): Cannot list models - GEMINI_API_KEY is not set.")
        return []

    # Ensure genai is configured. If initial configuration failed, model_instance would be None.
    # Re-attempting configure here might be useful if the initial one failed for a transient reason,
    # but generally, if it failed at startup, it will likely fail here too.
    # A simple check if genai is configured (non-public API, use with caution or remove)
    if hasattr(genai, '_is_configured') and not genai._is_configured:
        print("WARNING (list_models): genai client not configured. Attempting to re-configure.")
        try:
            genai.configure(api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"ERROR (list_models): Failed to re-configure genai client: {e}")
            return []

    print("\n--- Listing Available Generative Models (supporting 'generateContent') ---")
    valid_models_for_content = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_info = {
                    "name": m.name,
                    "display_name": m.display_name,
                    "version": m.version,
                    "supported_generation_methods": m.supported_generation_methods
                }
                valid_models_for_content.append(model_info)
                print(f"  Model: {m.name} (Version: {m.version}, Supports: {', '.join(m.supported_generation_methods)})")

        if not valid_models_for_content:
            print("  No models found that support 'generateContent' for your API key.")
        else:
            print(f"  Found {len(valid_models_for_content)} model(s) supporting 'generateContent'.")
    except Exception as e:
        print(f"ERROR (list_models): Could not retrieve models from API: {e}")
    print("--- End of Model List ---")
    return valid_models_for_content

# --- Main Function to Get Gemini Response ---
def get_gemini_response(user_input: str) -> str:
    global model_instance # Allow re-assignment if re-initialization occurs

    print(f"DEBUG (get_gemini_response): Called with user_input. Current model_instance is {'VALID' if model_instance else 'None'}. API Key available: {GEMINI_API_KEY is not None}. Chosen model: {CHOSEN_MODEL_NAME}")

    if not model_instance:
        if GEMINI_API_KEY and CHOSEN_MODEL_NAME:
            print(f"WARNING (get_gemini_response): Model instance for '{CHOSEN_MODEL_NAME}' was not initialized or was reset. Retrying initialization now.")
            try:
                # Ensure genai is configured before creating model. This might be redundant if startup config was successful
                # but helpful if some state was lost or never achieved.
                genai.configure(api_key=GEMINI_API_KEY)
                model_instance = genai.GenerativeModel(CHOSEN_MODEL_NAME)
                print(f"INFO (get_gemini_response): Successfully re-initialized model '{CHOSEN_MODEL_NAME}'.")
            except Exception as e:
                print(f"ERROR (get_gemini_response): Failed to re-initialize model '{CHOSEN_MODEL_NAME}': {e}")
                return "Gemini client error: Failed to re-initialize model. Check API key and model name. Details in server log."
        else:
            # This means either API key or model name (or both) are missing.
            missing_info = []
            if not GEMINI_API_KEY: missing_info.append("API key missing")
            if not CHOSEN_MODEL_NAME: missing_info.append("model name not specified")
            return f"Gemini client error: {', '.join(missing_info)}; model not initialized."

    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        response = model_instance.generate_content(user_input, safety_settings=safety_settings)

        # Accessing response.text can implicitly call response.resolve() if not yet resolved.
        # It's better to check parts or prompt_feedback first if text is empty.
        if response.parts:
            return "".join(part.text for part in response.parts if hasattr(part, 'text')) # Ensure all parts are concatenated
        elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            return f"Response blocked by Gemini due to: {response.prompt_feedback.block_reason}."
        else:
            # This block is for when there are no parts and no explicit block reason.
            # It might be an issue with the API key not validated until the first actual generation call.
            # Forcing resolve here can surface such errors.
            try:
                # If response.text was tried and was empty, and no parts, this might raise error
                # This might be redundant if accessing response.text already tried to resolve.
                if hasattr(response, '_done') and not response._done: # Non-public, indicates if resolve was called
                     response.resolve()
                # After resolve, check parts again
                if response.parts: return "".join(part.text for part in response.parts if hasattr(part, 'text'))
                print(f"DEBUG (get_gemini_response): Gemini response empty, no parts, no block reason. Raw response: {response}")
                return "Gemini returned an empty or unexpected response. Please check server logs for details."
            except Exception as e_resolve:
                 print(f"ERROR (get_gemini_response): Error during response.resolve() or accessing parts post-resolve: {e_resolve}")
                 error_message = str(e_resolve).lower()
                 if "api key not valid" in error_message: return "Gemini API Error: API key reported as invalid during generation."
                 return f"Gemini error after attempting to resolve response: {e_resolve}"

    except Exception as e:
        error_message_str = str(e).lower()
        current_model_name_for_error = model_instance.model_name if model_instance and hasattr(model_instance, 'model_name') else CHOSEN_MODEL_NAME
        print(f"ERROR (get_gemini_response): API call failed for model '{current_model_name_for_error}': {error_message_str}")
        if "api key not valid" in error_message_str or "invalid api key" in error_message_str:
            return "Gemini API Error: API key invalid or permission issues. Check Google Cloud Console."
        elif "models/" in error_message_str and ("not found" in error_message_str or "is not supported" in error_message_str):
            return f"Gemini API Error: Model '{current_model_name_for_error}' not found/supported for 'generateContent'. (Details: {e})"
        elif "quota" in error_message_str or "resource_exhausted" in error_message_str:
            return "Gemini API Error: Project quota exceeded."
        elif "deadline_exceeded" in error_message_str or "service_unavailable" in error_message_str:
            return "Gemini API Error: The service is temporarily unavailable or the request timed out. Please try again later."
        return f"Unexpected error with Gemini service: {e}"

# --- Direct Test / Model Lister Block ---
if __name__ == '__main__':
    print("\n--- Gemini Client Direct Execution: Model Lister & Test ---")
    if not GEMINI_API_KEY:
        print("Run Status: FAILED - GEMINI_API_KEY is not set in environment.")
    else:
        print(f"Initial model_instance status for '{CHOSEN_MODEL_NAME}': {'Set' if model_instance else 'None (will attempt re-init if needed)'}")
        print("\nAttempting to list available models for your API key...")
        available_models = list_available_models_for_api_key()

        if not available_models:
            print("\nINFO: No models supporting 'generateContent' were found. Cannot test generateContent.")
        else:
            print(f"\nINFO: Default CHOSEN_MODEL_NAME in script is currently '{CHOSEN_MODEL_NAME}'.")
            is_chosen_model_available = any(m['name'] == CHOSEN_MODEL_NAME for m in available_models)
            if not is_chosen_model_available:
                print(f"WARNING: The current CHOSEN_MODEL_NAME ('{CHOSEN_MODEL_NAME}') does NOT appear in your list of available models supporting 'generateContent'.")
                print("         'get_gemini_response' will likely fail or use a different model if this name is invalid.")
            else:
                print(f"         The CHOSEN_MODEL_NAME ('{CHOSEN_MODEL_NAME}') is in your list of available models.")

            # Test generateContent with CHOSEN_MODEL_NAME.
            # get_gemini_response will attempt to initialize model_instance if it's None.
            print(f"\n--- Testing generateContent with CHOSEN_MODEL_NAME: {CHOSEN_MODEL_NAME} ---")
            test_queries = {"Greeting": "Hello, who are you?", "Fact": "What's the capital of France?"}
            for desc, query in test_queries.items():
                print(f"  Query ({desc}): \"{query}\"")
                response = get_gemini_response(query)
                print(f"  Response: \"{response}\"\n")

    print("--- End of Direct Execution ---")
