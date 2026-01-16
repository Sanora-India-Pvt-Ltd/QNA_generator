"""
Main entry point for Universal Profile Builder
"""

import sys
import os
from universal_profile_builder import UniversalProfileBuilder
from config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID

def main():
    """Main function"""
    
    # Check credentials
    if GOOGLE_CSE_API_KEY == "YOUR_GOOGLE_CSE_API_KEY_HERE" or GOOGLE_CSE_ID == "YOUR_GOOGLE_CSE_ENGINE_ID_HERE":
        print("⚠️  ERROR: Please configure your Google CSE credentials in config.py")
        sys.exit(1)
    
    # Initialize builder
    builder = UniversalProfileBuilder(GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID)
    
    print("\n" + "="*60)
    print("UNIVERSAL PROFILE BUILDER")
    print("="*60)
    print("\nProvide at least ONE anchor (never name only):")
    print("  - Official website/domain (best)")
    print("  - Employer/organization")
    print("  - City/country")
    print("  - Unique handle")
    print("  - Known page (Wikipedia, etc.)")
    print("\n" + "="*60)
    
    # Get inputs
    name = input("\nName (optional): ").strip() or None
    domain = input("Domain/website (optional): ").strip() or None
    organization = input("Organization/company (optional): ").strip() or None
    city = input("City (optional): ").strip() or None
    handle = input("Handle/social (optional): ").strip() or None
    known_page = input("Known page URL (optional): ").strip() or None
    
    # Validate at least one anchor
    if not any([domain, organization, city, handle, known_page]):
        print("\n❌ ERROR: Must provide at least one anchor (domain, organization, city, handle, or known page)")
        print("   Never build from name only!")
        sys.exit(1)
    
    # Build profile
    try:
        result = builder.build_profile(
            name=name,
            domain=domain,
            organization=organization,
            city=city,
            handle=handle,
            known_page=known_page
        )
        
        if 'error' in result:
            print(f"\n❌ {result['error']}")
            sys.exit(1)
        
        # Print formatted results
        confirmed_facts_list = result.pop('_confirmed_facts_list', [])  # Remove before JSON save
        formatted_output = builder.format_output(result, confirmed_facts_list)
        print(formatted_output)
        
        # Save results (without FactCandidate objects)
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"profile_{result['verified_identity']['name'] or 'unknown'}.json")
        
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
        print("\n✅ Profile building completed!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
