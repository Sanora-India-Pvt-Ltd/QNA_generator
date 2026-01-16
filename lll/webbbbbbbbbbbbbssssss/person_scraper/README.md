# Universal Person About Table Builder

Scrapes **publicly available** web data to build structured About tables for any person.

## 🔄 Workflow

```
User Consent
   ↓
Google Programmable Search Engine (CSE)
   ↓
List of public URLs
   ↓
requests.get(url)
   ↓
BeautifulSoup parses HTML
   ↓
Extract facts (bio, role, experience)
   ↓
Build About table for all universal persons
```

## ✨ Features

- ✅ **User Consent** - Explicit permission before scraping
- ✅ **Google CSE Integration** - Finds relevant public URLs
- ✅ **Web Scraping** - Extracts content from public pages
- ✅ **Fact Extraction** - Identifies profession, experience, contact info
- ✅ **Structured Output** - Clean About table format
- ✅ **Respectful Scraping** - Rate limiting and proper headers

## 📋 Requirements

- Python 3.7+
- Google Custom Search Engine API key
- Internet connection

## 🚀 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Google CSE Credentials

1. **Create Custom Search Engine:**
   - Go to: https://cse.google.com/cse/all
   - Click "Add" to create a new search engine
   - Set it to search the entire web
   - Note your **Search Engine ID** (CX)

2. **Get API Key:**
   - Go to: https://console.developers.google.com/
   - Enable "Custom Search API"
   - Create credentials (API Key)
   - Note your **API Key**

### 3. Configure Credentials

Edit `config.py`:

```python
GOOGLE_CSE_API_KEY = "your_api_key_here"
GOOGLE_CSE_ID = "your_search_engine_id_here"
```

## 💻 Usage

### Command Line

```bash
# Interactive mode
python main.py

# Direct mode
python main.py "Dr. Sanjay Arora"
```

### Python Script

```python
from scraper import PersonScraper

# Initialize
scraper = PersonScraper(
    google_cse_api_key="your_key",
    google_cse_id="your_id"
)

# Scrape person
result = scraper.scrape_person("Dr. Sanjay Arora", max_urls=10)

# Print About table
scraper.print_about_table("Dr. Sanjay Arora")

# Save results
scraper.save_results("Dr. Sanjay Arora", "output.json")
```

## 📊 Output Format

### About Table (Console)

```
============================================================
ABOUT TABLE - DR. SANJAY ARORA
============================================================

Full Name            | Dr. Sanjay Arora
Profession           | Dentist, Endodontist, TMJ Specialist
Roles                | CEO, Founder
Experience           | 30 years
Companies            | Zental Dental, TMJ Helpline
Location             | New Delhi, India
Websites             | https://tmjhelpline.com, https://zentaldental.com
Email                | tmjhelpline@gmail.com
Phone                | +91-9999999702
Bio                  | Dr. Sanjay Arora is a veteran dentist...
```

### JSON Output

```json
{
  "about_table": {
    "Full Name": "Dr. Sanjay Arora",
    "Profession": "Dentist, Endodontist, TMJ Specialist",
    "Roles": "CEO, Founder",
    "Experience": "30 years",
    "Companies": "Zental Dental, TMJ Helpline",
    "Location": "New Delhi, India",
    "Websites": "https://tmjhelpline.com",
    "Email": "tmjhelpline@gmail.com",
    "Phone": "+91-9999999702",
    "Bio": "Dr. Sanjay Arora is a veteran dentist..."
  },
  "raw_facts": {
    "full_name": "Dr. Sanjay Arora",
    "profession": ["Dentist", "Endodontist"],
    "experience_years": 30,
    "companies": ["Zental Dental"],
    "locations": ["New Delhi", "India"],
    "websites": ["https://tmjhelpline.com"],
    "email": ["tmjhelpline@gmail.com"],
    "phone": ["+91-9999999702"],
    "bio_snippets": ["Dr. Sanjay Arora is a veteran dentist..."]
  },
  "scraped_urls": [
    "https://tmjhelpline.com",
    "https://zentaldental.com"
  ],
  "timestamp": "2024-01-15 10:30:00"
}
```

## 🔍 What Gets Extracted

- **Full Name** - Person's name
- **Profession** - Job titles, specializations
- **Roles** - Current/past positions
- **Experience** - Years of experience
- **Companies** - Organizations associated with
- **Location** - Cities, countries
- **Websites** - Personal/professional websites
- **Email** - Public email addresses
- **Phone** - Contact numbers
- **Bio** - Biography snippets

## ⚠️ Important Notes

### ✅ What This Scrapes

- Public websites and profiles
- Business listings
- Public interviews/articles
- Conference listings
- Awards and recognitions
- LinkedIn profiles (public)
- Google Business listings

### ❌ What This Does NOT Scrape

- Private data or databases
- Information behind logins/paywalls
- Leaked or unauthorized data
- Social media private profiles
- Email content
- Private messages

### 🔒 Legal & Ethical

- **Always get user consent** before scraping
- **Respect robots.txt** (consider adding)
- **Rate limit requests** (1 second delay default)
- **Only use public data**
- **Comply with website terms of service**

## 🛠️ Customization

### Adjust Scraping Settings

Edit `config.py`:

```python
MAX_URLS_TO_SCRAPE = 20  # Scrape more URLs
REQUEST_DELAY_SECONDS = 2  # Slower rate limiting
REQUIRE_CONSENT = False  # Skip consent (not recommended)
```

### Customize Fact Extraction

Edit `scraper.py` → `extract_facts()` method to:
- Add new extraction patterns
- Modify regex patterns
- Add custom fields

### Add New Output Formats

Edit `scraper.py` → `build_about_table()` to:
- Change table structure
- Add new fields
- Format differently

## 🐛 Troubleshooting

### "Please configure your Google CSE credentials"

- Make sure `config.py` has your API key and CSE ID
- Verify credentials are correct

### "Error searching Google CSE"

- Check API key is valid
- Verify CSE ID is correct
- Check API quota limits

### "Failed to scrape URL"

- Website might be blocking requests
- URL might be inaccessible
- Check internet connection

### No results found

- Person might not have public web presence
- Try different name variations
- Increase `MAX_URLS_TO_SCRAPE`

## 📝 License

Use responsibly. Only scrape public data with consent.

## 🤝 Contributing

Feel free to:
- Add more extraction patterns
- Improve fact extraction accuracy
- Add support for more data sources
- Enhance output formats

---

**Remember:** Always get user consent and only scrape publicly available data!
