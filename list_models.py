"""
List available Gemini models for your API key
Run this to see which models are available on your account
"""

from google import genai
import os
import sys

def list_available_models():
    """List all available Gemini models"""
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  PowerShell: $env:GEMINI_API_KEY='your-key-here'")
        print("  Or get a free key at: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    try:
        print("Connecting to Gemini API...")
        client = genai.Client(api_key=api_key)
        
        print("\n" + "="*60)
        print("Available Gemini Models:")
        print("="*60)
        
        models = list(client.models.list())
        
        if not models:
            print("No models found. Check your API key.")
            return
        
        for model in models:
            print(f"  ✓ {model.name}")
        
        print("\n" + "="*60)
        print("💡 Use one of these model names in your code!")
        print("   Example: 'models/gemini-1.5-flash'")
        print("="*60)
        
        # Suggest the first model as default
        if models:
            suggested = models[0].name
            print(f"\n🎯 Suggested model: {suggested}")
            print(f"   Use this in your code: model='{suggested}'")
        
    except ImportError:
        print("❌ Error: google-genai not installed")
        print("\nInstall with: pip install --upgrade google-genai")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nCheck:")
        print("  1. Your API key is correct")
        print("  2. You have internet connection")
        print("  3. google-genai is installed: pip install --upgrade google-genai")
        sys.exit(1)

if __name__ == "__main__":
    list_available_models()


