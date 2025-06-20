import google.generativeai as genai
import os

# Configure your API key
# Make sure to replace "YOUR_API_KEY" with your actual Gemini API key
# It's highly recommended to use environment variables for API keys
# For example: genai.configure(api_key=os.environ["GEMINI_API_KEY"])
genai.configure(api_key="AIzaSyAeLVQtUBBCaqTfEZcV--hZC16CvstRcic") 

print("Listing available models:")
for m in genai.list_models():
    # Only print models that support the 'generateContent' method
    if "generateContent" in m.supported_generation_methods:
        print(f"Name: {m.name}, Display Name: {m.display_name}")

