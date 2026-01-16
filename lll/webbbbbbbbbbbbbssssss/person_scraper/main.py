"""
Main entry point for Universal Person About Table Builder
"""

import sys
import os
from scraper import PersonScraper, IdentityFingerprint
from config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID, MAX_URLS_TO_SCRAPE

def create_identity_fingerprint(person_name: str) -> IdentityFingerprint:
    """
    Create identity fingerprint based on person name
    You can customize this for specific people
    """
    
    # Example: Dr. Sanjay Arora (TMJ Dentist)
    if "sanjay arora" in person_name.lower() and "dr" in person_name.lower():
        return IdentityFingerprint(
            allowed_domains=[
                'zentaldental.com',
                'tmjhelpline.com',
                'tmjhelpline.in',
                'bodypainshelpline.com'
            ],
            cities=['new delhi', 'delhi', 'green park', 'saket'],
            specialty_keywords=['dentist', 'endodontist', 'tmj', 'occlusion', 'dental'],
            clinic_keywords=['zental', 'tmj helpline', 'body pain'],
            required_matches=2
        )
    
    # Default: Generic fingerprint (less strict)
    return None

def main():
    """Main function to run the scraper"""
    
    # Check if credentials are set
    if GOOGLE_CSE_API_KEY == "YOUR_GOOGLE_CSE_API_KEY_HERE" or GOOGLE_CSE_ID == "YOUR_GOOGLE_CSE_ENGINE_ID_HERE":
        print("⚠️  ERROR: Please configure your Google CSE credentials in config.py")
        print("\nTo get your credentials:")
        print("1. Go to: https://developers.google.com/custom-search/v1/overview")
        print("2. Create a Custom Search Engine: https://cse.google.com/cse/all")
        print("3. Get your API key from: https://console.developers.google.com/")
        print("4. Update config.py with your credentials")
        sys.exit(1)
    
    # Get person name from user
    if len(sys.argv) > 1:
        person_name = ' '.join(sys.argv[1:])
    else:
        person_name = input("\nEnter person's name to scrape: ").strip()
    
    if not person_name:
        print("Error: Person name is required")
        sys.exit(1)
    
    # Create identity fingerprint (if available)
    identity_fingerprint = create_identity_fingerprint(person_name)
    
    if identity_fingerprint:
        print(f"✓ Using identity fingerprint for disambiguation")
        print(f"  Required matches: {identity_fingerprint.required_matches}")
    
    # Initialize scraper
    scraper = PersonScraper(
        GOOGLE_CSE_API_KEY, 
        GOOGLE_CSE_ID,
        identity_fingerprint=identity_fingerprint,
        strict_mode=False  # Set to True for allowlist-only mode
    )
    
    # Scrape and build About table
    try:
        result = scraper.scrape_person(person_name, max_urls=MAX_URLS_TO_SCRAPE)
        
        if 'error' in result:
            print(f"\n❌ {result['error']}")
            sys.exit(1)
        
        # Print results
        scraper.print_about_table(person_name)
        
        # Save results
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"about_{person_name.replace(' ', '_')}.json")
        scraper.save_results(person_name, output_file)
        
        print("\n✅ Scraping completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
