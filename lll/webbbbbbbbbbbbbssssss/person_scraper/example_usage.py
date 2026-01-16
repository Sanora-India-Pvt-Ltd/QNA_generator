"""
Example usage of Person Scraper
Demonstrates how to use the scraper programmatically
"""

from scraper import PersonScraper

# Example 1: Basic usage
def example_basic():
    """Basic scraping example"""
    
    # Initialize scraper (replace with your credentials)
    scraper = PersonScraper(
        google_cse_api_key="YOUR_API_KEY",
        google_cse_id="YOUR_CSE_ID"
    )
    
    # Scrape a person
    result = scraper.scrape_person("Dr. Sanjay Arora", max_urls=5)
    
    # Print results
    scraper.print_about_table("Dr. Sanjay Arora")
    
    # Save to file
    scraper.save_results("Dr. Sanjay Arora", "dr_sanjay_arora.json")


# Example 2: Batch processing
def example_batch():
    """Scrape multiple people"""
    
    scraper = PersonScraper(
        google_cse_api_key="YOUR_API_KEY",
        google_cse_id="YOUR_CSE_ID"
    )
    
    people = [
        "Dr. Sanjay Arora",
        "Elon Musk",
        "Sundar Pichai"
    ]
    
    for person in people:
        print(f"\n{'='*60}")
        print(f"Processing: {person}")
        print(f"{'='*60}")
        
        result = scraper.scrape_person(person, max_urls=5)
        
        if 'error' not in result:
            scraper.print_about_table(person)
            scraper.save_results(person, f"output/about_{person.replace(' ', '_')}.json")


# Example 3: Custom extraction
def example_custom():
    """Custom extraction with manual URL scraping"""
    
    scraper = PersonScraper(
        google_cse_api_key="YOUR_API_KEY",
        google_cse_id="YOUR_CSE_ID"
    )
    
    # Search for URLs
    urls = scraper.search_google_cse("Dr. Sanjay Arora dentist", max_results=5)
    
    # Scrape specific URLs
    scraped = []
    for url_info in urls:
        content = scraper.scrape_url(url_info['url'])
        if content:
            scraped.append(content)
    
    # Extract facts
    facts = scraper.extract_facts(scraped, "Dr. Sanjay Arora")
    
    # Build table
    about_table = scraper.build_about_table(facts)
    
    # Print
    print("\nCustom About Table:")
    for key, value in about_table.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    print("This is an example file.")
    print("Update with your Google CSE credentials and run.")
    print("\nSee README.md for setup instructions.")
