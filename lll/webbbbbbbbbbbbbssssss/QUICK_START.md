# Quick Start Guide

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r person_scraper/requirements.txt
   ```

2. **Get Google CSE credentials:**
   - Create Custom Search Engine: https://cse.google.com/cse/all
   - Get API Key: https://console.developers.google.com/

3. **Configure credentials:**
   Edit `person_scraper/config.py`:
   ```python
   GOOGLE_CSE_API_KEY = "your_actual_api_key"
   GOOGLE_CSE_ID = "your_actual_cse_id"
   ```

## Run

From the root directory:
```bash
python main.py "Dr. Sanjay Arora"
```

Or from person_scraper directory:
```bash
cd person_scraper
python main.py "Dr. Sanjay Arora"
```

## Output

Results will be saved to `output/about_Dr_Sanjay_Arora.json`
