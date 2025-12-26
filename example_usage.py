"""
Example usage of YouTube Quiz Generator
Shows how to use both Gemini (free) and OpenAI
"""

from youtube_quiz_generator import YouTubeQuizGenerator
import os

def example_gemini():
    """Example using Gemini (FREE - Recommended!)"""
    
    # Get Gemini API key from environment or set it here
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable")
        print("Get free key at: https://makersuite.google.com/app/apikey")
        return
    
    # Initialize the generator with Gemini
    generator = YouTubeQuizGenerator(
        llm_provider="gemini",
        api_key=api_key
    )
    
    # Example YouTube URL (replace with your video)
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with actual video
    
    try:
        # Process the video and generate questions
        print("Processing YouTube video with Gemini...")
        results = generator.process(youtube_url, num_questions=20)
        
        # Print the questions
        generator.print_questions(results)
        
        # Save results to a file
        generator.save_results(results, "example_quiz_gemini.json")
        
        print("\n✅ Success! Check 'example_quiz_gemini.json' for the full results.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def example_openai():
    """Example using OpenAI"""
    
    # Get OpenAI API key from environment or set it here
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    # Initialize the generator with OpenAI
    generator = YouTubeQuizGenerator(
        llm_provider="openai",
        api_key=api_key
    )
    
    # Example YouTube URL (replace with your video)
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with actual video
    
    try:
        # Process the video and generate questions
        print("Processing YouTube video with OpenAI...")
        results = generator.process(youtube_url, num_questions=20)
        
        # Print the questions
        generator.print_questions(results)
        
        # Save results to a file
        generator.save_results(results, "example_quiz_openai.json")
        
        print("\n✅ Success! Check 'example_quiz_openai.json' for the full results.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("="*60)
    print("YouTube Quiz Generator - Example Usage")
    print("="*60)
    print("\n1. Using Gemini (FREE - Recommended)")
    print("2. Using OpenAI")
    
    choice = input("\nEnter choice (1 or 2, default: 1): ").strip() or "1"
    
    if choice == "1":
        example_gemini()
    else:
        example_openai()


