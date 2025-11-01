import google.generativeai as genai

# Configure your Gemini API key
genai.configure(api_key="AIzaSyB87k8kALec7yPKR6fYySgi19HA0hwCGnw")

# List available models
models = genai.list_models()
for m in models:
    print(m.name, "-", getattr(m, "capabilities", []))