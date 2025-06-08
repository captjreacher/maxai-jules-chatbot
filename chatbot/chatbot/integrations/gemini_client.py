import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')) # Adjusted for chatbot/chatbot/integrations
dotenv_path = os.path.join(project_root, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"INFO: .env file loaded from {dotenv_path}")
else:
    if load_dotenv(): # Try loading from CWD as a fallback
        print("INFO: .env file loaded from current working directory or via dotenv default search.")
    else:
        print("WARNING: .env file not found at project root or CWD. API key may not be available.")

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
CHOSEN_MODEL_NAME = 'models/gemini-1.5-flash-latest'  # Default model, will be checked against available list
model_instance = None

if not GEMINI_API_KEY:
    print("CRITICAL: GEMINI_API_KEY not found in environment. Gemini features will be disabled.")
else:
    masked_key = GEMINI_API_KEY[:4] + "****" + GEMINI_API_KEY[-4:] if len(GEMINI_API_KEY) > 8 else "key_masked"
    print(f"INFO: Found GEMINI_API_KEY (masked): {masked_key}")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Try to initialize with the CHOSEN_MODEL_NAME. This might fail if the model is not available.
        model_instance = genai.GenerativeModel(CHOSEN_MODEL_NAME)
        print(f"INFO: Google Generative AI client configured. Default model to attempt for 'get_gemini_response': '{CHOSEN_MODEL_NAME}'.")
    except Exception as e:
        print(f"WARNING: Failed to initialize default model '{CHOSEN_MODEL_NAME}' at startup: {e}")
        print("         This might be normal if the model name needs to be changed. Model listing will proceed.")
        model_instance = None # Ensure it's None if startup initialization fails

# --- Utility Function to List Models ---
def list_available_models_for_api_key():
    """Lists models available to the configured API key that support 'generateContent'."""
    if not GEMINI_API_KEY:
        print("ERROR (list_models): Cannot list models - GEMINI_API_KEY is not set.")
        return []

    # Check if genai.configure has been called successfully.
    # genai._is_configured is not public; rely on successful execution of genai.configure() at startup.
    # If API key is present but genai.configure failed, model_instance would be None.
    # If genai.configure was never called (e.g. API key missing), this function shouldn't be reached or will fail.

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
    global model_instance # Allow modification of the global instance if re-initialization is attempted
    if not model_instance:
        if GEMINI_API_KEY and CHOSEN_MODEL_NAME:
            print(f"WARNING (get_gemini_response): Model instance for '{CHOSEN_MODEL_NAME}' was not initialized at startup. Retrying now.")
            try:
                model_instance = genai.GenerativeModel(CHOSEN_MODEL_NAME) # Attempt to re-initialize
                print(f"INFO (get_gemini_response): Successfully re-initialized model '{CHOSEN_MODEL_NAME}'.")
            except Exception as e:
                print(f"ERROR (get_gemini_response): Failed to re-initialize model '{CHOSEN_MODEL_NAME}': {e}")
                return f"Gemini client error: Model '{CHOSEN_MODEL_NAME}' could not be initialized. Check logs."
        else:
            # This case means either API key is missing, or CHOSEN_MODEL_NAME is somehow not set (though it has a default)
            return "Gemini client error: API key missing or no model name specified; model not initialized."

    try:
        safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}] # Example
        response = model_instance.generate_content(user_input, safety_settings=safety_settings)
        if response.parts:
            return "".join(part.text for part in response.parts if hasattr(part, 'text'))
        elif hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            return f"Response blocked by Gemini: {response.prompt_feedback.block_reason}."
        else:
            return "Gemini returned an empty or unexpected response."
    except Exception as e:
        error_message = str(e).lower()
        # Use model_instance.model_name if available, otherwise fallback to CHOSEN_MODEL_NAME for error reporting
        model_name_in_error = model_instance.model_name if model_instance and hasattr(model_instance, 'model_name') else CHOSEN_MODEL_NAME
        print(f"ERROR (get_gemini_response): API call failed for model '{model_name_in_error}': {error_message}")
        if "api key not valid" in error_message or ("permission_denied" in error_message and "api key" in error_message):
            return "Gemini API Error: API key invalid or permission issues. Check Google Cloud Console."
        elif "models/" in error_message and ("not found" in error_message or "is not supported" in error_message): # More specific model error
            return f"Gemini API Error: Model '{model_name_in_error}' not found or not supported for 'generateContent'. (Details: {e})"
        elif "quota" in error_message:
            return "Gemini API Error: Project quota exceeded."
        return f"Unexpected error with Gemini service using model '{model_name_in_error}': {e}"

# --- Direct Test / Model Lister Block (Corrected Order) ---
if __name__ == '__main__':
    print("\n--- Gemini Client Direct Execution: Model Lister & Test ---")
    if not GEMINI_API_KEY:
        print("Run Status: FAILED - GEMINI_API_KEY is not set in environment.")
    else:
        # STEP 1: List available models for the API key
        print("\nSTEP 1: Listing available models for your API key...")
        available_models = list_available_models_for_api_key()

        # STEP 2: Provide information based on the listed models and CHOSEN_MODEL_NAME
        print(f"\nSTEP 2: Checking configured model ('{CHOSEN_MODEL_NAME}') against available models...")
        if not available_models:
            print("  INFO: No models supporting 'generateContent' were found. Cannot test 'generateContent'.")
            print("        Please check your Google Cloud project permissions for the Generative Language API.")
        else:
            is_chosen_model_available = any(m['name'] == CHOSEN_MODEL_NAME for m in available_models)
            if is_chosen_model_available:
                print(f"  INFO: The CHOSEN_MODEL_NAME ('{CHOSEN_MODEL_NAME}') is in your list of available models.")
                if not model_instance: # If instance wasn't created at startup even if model name is valid
                    print(f"  WARNING: However, the instance for '{CHOSEN_MODEL_NAME}' was not successfully created at startup (check earlier logs). 'get_gemini_response' will attempt to re-initialize it.")
            else:
                print(f"  WARNING: The CHOSEN_MODEL_NAME ('{CHOSEN_MODEL_NAME}') does NOT appear in your list of available models supporting 'generateContent'.")
                print("           You MUST update CHOSEN_MODEL_NAME in the script to one of the listed models for 'get_gemini_response' to work.")
                print(f"           Available model names (supporting generateContent): {[m['name'] for m in available_models]}")

            # STEP 3: Conditionally test generateContent
            # Test if CHOSEN_MODEL_NAME is available, rely on get_gemini_response to initialize if needed.
            if is_chosen_model_available:
                print(f"\nSTEP 3: Testing 'generateContent' with CHOSEN_MODEL_NAME: {CHOSEN_MODEL_NAME} ---")
                test_queries = {"Greeting": "Hello, who are you?", "Fact": "What's the capital of France?"}
                for desc, query in test_queries.items():
                    print(f"  Query ({desc}): \"{query}\"")
                    response = get_gemini_response(query) # This will use CHOSEN_MODEL_NAME
                    print(f"  Response: \"{response}\"\n")
            elif model_instance : # model_instance exists but CHOSEN_MODEL_NAME is not in available_models (edge case)
                 print(f"\nSTEP 3: Test with CHOSEN_MODEL_NAME ('{CHOSEN_MODEL_NAME}') SKIPPED because it's not in your list of available models, though an instance for it was somehow created.")
            else: # No instance AND chosen model is not available
                 print(f"\nSTEP 3: Test with CHOSEN_MODEL_NAME ('{CHOSEN_MODEL_NAME}') SKIPPED. It's not in your available models list or its instance could not be created.")
                 if not is_chosen_model_available and available_models: # Guide user if other models are available
                     print("          Please update CHOSEN_MODEL_NAME in the script to one of the models listed in STEP 2 and retry.")

    print("--- End of Direct Execution ---")
