"""
Universal Person About Table Builder - IMPROVED VERSION
With identity disambiguation, content extraction, and evidence-gated facts
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import re

try:
    from readability import Document
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False
    print("⚠️  readability-lxml not installed. Install with: pip install readability-lxml")
    print("   Falling back to basic content extraction.")


class IdentityFingerprint:
    """Target Identity Fingerprint for disambiguation"""
    
    def __init__(self, 
                 allowed_domains: List[str] = None,
                 cities: List[str] = None,
                 specialty_keywords: List[str] = None,
                 clinic_keywords: List[str] = None,
                 required_matches: int = 2):
        """
        Initialize identity fingerprint
        
        Args:
            allowed_domains: List of allowed website domains
            cities: List of associated cities
            specialty_keywords: List of specialty/profession keywords
            clinic_keywords: List of clinic/business keywords
            required_matches: Minimum number of anchor matches required
        """
        self.allowed_domains = [d.lower() for d in (allowed_domains or [])]
        self.cities = [c.lower() for c in (cities or [])]
        self.specialty_keywords = [k.lower() for k in (specialty_keywords or [])]
        self.clinic_keywords = [k.lower() for k in (clinic_keywords or [])]
        self.required_matches = required_matches
    
    def matches(self, url: str, page_text: str) -> Tuple[bool, int, List[str]]:
        """
        Check if URL/page matches identity fingerprint
        
        Returns:
            (matches, match_count, matched_anchors)
        """
        url_lower = url.lower()
        text_lower = page_text.lower()
        
        matches = []
        match_count = 0
        
        # Check allowed domains
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().replace('www.', '')
        for allowed in self.allowed_domains:
            if allowed in domain:
                matches.append(f"domain:{allowed}")
                match_count += 1
                break
        
        # Check cities
        for city in self.cities:
            if city in text_lower:
                matches.append(f"city:{city}")
                match_count += 1
                break
        
        # Check specialty keywords
        for keyword in self.specialty_keywords:
            if keyword in text_lower:
                matches.append(f"specialty:{keyword}")
                match_count += 1
                break
        
        # Check clinic keywords
        for keyword in self.clinic_keywords:
            if keyword in text_lower:
                matches.append(f"clinic:{keyword}")
                match_count += 1
                break
        
        return (match_count >= self.required_matches, match_count, matches)


class PersonScraper:
    """Scrapes public web data to build About tables for any person"""
    
    # Domain denylist (high impact)
    DENYLIST_DOMAINS = [
        'linkedin.com',
        'facebook.com',
        'instagram.com',
        'twitter.com',
        'youtube.com',
        'pinterest.com',
        'tiktok.com',
    ]
    
    # Domain allowlist (optional, for strict mode)
    ALLOWLIST_DOMAINS = None  # Set to list of domains for strict mode
    
    def __init__(self, 
                 google_cse_api_key: str, 
                 google_cse_id: str,
                 identity_fingerprint: IdentityFingerprint = None,
                 strict_mode: bool = False):
        """
        Initialize scraper with Google CSE credentials
        
        Args:
            google_cse_api_key: Your Google Custom Search API key
            google_cse_id: Your Google Custom Search Engine ID
            identity_fingerprint: Identity fingerprint for disambiguation
            strict_mode: If True, only scrape allowlisted domains
        """
        self.api_key = google_cse_api_key
        self.cse_id = google_cse_id
        self.identity_fingerprint = identity_fingerprint
        self.strict_mode = strict_mode
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.scraped_data = {}
        
    def get_user_consent(self, person_name: str) -> bool:
        """Get user consent before scraping"""
        print(f"\n{'='*60}")
        print(f"CONSENT REQUEST - Public Data Scraping")
        print(f"{'='*60}")
        print(f"Person: {person_name}")
        print(f"\nI will only scrape PUBLICLY AVAILABLE information:")
        print("  ✓ Public websites and profiles")
        print("  ✓ Business listings")
        print("  ✓ Public interviews/articles")
        print("  ✓ Conference listings")
        print("  ✓ Awards and recognitions")
        print("\nI will NOT access:")
        print("  ✗ Private data or databases")
        print("  ✗ Information behind logins/paywalls")
        print("  ✗ Leaked or unauthorized data")
        print(f"\n{'='*60}")
        
        while True:
            response = input(f"\nDo you consent to scraping public data for '{person_name}'? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please enter 'yes' or 'no'")
    
    def is_allowed_domain(self, url: str) -> bool:
        """Check if domain is allowed (not denylisted, and allowlisted if strict)"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        # Check denylist
        for denied in self.DENYLIST_DOMAINS:
            if denied in domain:
                return False
        
        # Check allowlist (if strict mode)
        if self.strict_mode and self.ALLOWLIST_DOMAINS:
            for allowed in self.ALLOWLIST_DOMAINS:
                if allowed in domain:
                    return True
            return False
        
        return True
    
    def search_google_cse(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Google CSE for public URLs"""
        results = []
        num_results = min(max_results, 10)
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.api_key,
            'cx': self.cse_id,
            'q': query,
            'num': num_results
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'items' in data:
                for item in data['items']:
                    url_link = item.get('link', '')
                    # Filter by domain
                    if self.is_allowed_domain(url_link):
                        results.append({
                            'title': item.get('title', ''),
                            'url': url_link,
                            'snippet': item.get('snippet', ''),
                            'display_url': item.get('displayLink', '')
                        })
                    else:
                        print(f"  ⊘ Skipped denylisted domain: {url_link[:60]}...")
            
            print(f"✓ Found {len(results)} allowed URLs from Google CSE")
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Error searching Google CSE: {e}")
            return []
        except KeyError as e:
            print(f"✗ Error parsing Google CSE response: {e}")
            return []
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content using readability or fallback method"""
        
        # Try readability first
        if HAS_READABILITY:
            try:
                doc = Document(str(soup))
                content_html = doc.summary()
                content_soup = BeautifulSoup(content_html, 'html.parser')
                text = content_soup.get_text(separator=' ', strip=True)
                if len(text) > 200:  # Only use if substantial content
                    return text
            except Exception as e:
                print(f"    ⚠️  Readability failed: {e}, using fallback")
        
        # Fallback: Remove junk elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                            'aside', 'form', 'button', 'input', 'select',
                            'noscript', 'iframe', 'embed', 'object']):
            element.decompose()
        
        # Remove common junk classes/ids
        junk_selectors = [
            {'class': re.compile(r'cookie|banner|popup|modal|overlay|advertisement|ad-', re.I)},
            {'id': re.compile(r'cookie|banner|popup|modal|overlay|advertisement|ad-', re.I)},
        ]
        
        for selector in junk_selectors:
            for element in soup.find_all(**selector):
                element.decompose()
        
        # Get text from main content areas
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|article|post', re.I))
        
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def scrape_url(self, url: str) -> Optional[Dict]:
        """Scrape a single URL and extract main content"""
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main content (not navigation/junk)
            text = self.extract_main_content(soup)
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ''
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            return {
                'url': url,
                'title': title_text,
                'description': description,
                'text': text,
                'html': str(soup)
            }
            
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Failed to scrape {url}: {e}")
            return None
        except Exception as e:
            print(f"  ✗ Error parsing {url}: {e}")
            return None
    
    def extract_fact_with_evidence(self, 
                                   pattern: re.Pattern, 
                                   text: str, 
                                   context_window: int = 100) -> List[Dict]:
        """
        Extract facts with evidence snippets
        
        Returns:
            List of {value, evidence_snippet, source_url}
        """
        facts = []
        for match in pattern.finditer(text):
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            evidence = text[start:end].strip()
            
            facts.append({
                'value': match.group(0).strip(),
                'evidence_snippet': evidence,
                'match_start': match.start(),
                'match_end': match.end()
            })
        
        return facts
    
    def extract_facts(self, scraped_content: List[Dict], person_name: str) -> Dict:
        """
        Extract facts with evidence-gating and pattern-based extraction
        """
        facts = {
            'full_name': person_name,
            'profession': [],
            'roles': [],
            'experience_years': [],
            'education': [],
            'companies': [],
            'locations': [],
            'specializations': [],
            'awards': [],
            'websites': [],
            'email': [],
            'phone': [],
            'address': [],
            'bio_snippets': [],
        }
        
        # Combine all text for analysis
        all_pages = []
        for item in scraped_content:
            if item:
                all_pages.append({
                    'url': item['url'],
                    'text': item['text'],
                    'title': item.get('title', ''),
                    'description': item.get('description', '')
                })
        
        # Pattern-based extraction with evidence
        
        # 1. Email (strict regex)
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        for page in all_pages:
            email_facts = self.extract_fact_with_evidence(email_pattern, page['text'])
            for fact in email_facts:
                facts['email'].append({
                    'value': fact['value'],
                    'evidence': fact['evidence_snippet'],
                    'source_url': page['url']
                })
        
        # 2. Phone (strict regex - Indian formats)
        phone_patterns = [
            re.compile(r'\+91[-\s]?\d{10}'),
            re.compile(r'0\d{10}'),
            re.compile(r'\d{3}[-\s]?\d{3}[-\s]?\d{4}'),
        ]
        for pattern in phone_patterns:
            for page in all_pages:
                phone_facts = self.extract_fact_with_evidence(pattern, page['text'])
                for fact in phone_facts:
                    facts['phone'].append({
                        'value': fact['value'],
                        'evidence': fact['evidence_snippet'],
                        'source_url': page['url']
                    })
        
        # 3. Websites (from URLs in text and links)
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;!?]')
        for page in all_pages:
            url_facts = self.extract_fact_with_evidence(url_pattern, page['text'])
            for fact in url_facts:
                value = fact['value'].rstrip('.,;!?')
                # Only add if it's a real website (has domain)
                if '.' in value and len(value) > 10:
                    facts['websites'].append({
                        'value': value,
                        'evidence': fact['evidence_snippet'],
                        'source_url': page['url']
                    })
        
        # 4. Profession/Specialty (keyword-based)
        profession_keywords = [
            'dentist', 'doctor', 'physician', 'surgeon', 'endodontist',
            'orthodontist', 'periodontist', 'engineer', 'lawyer', 'ca',
            'accountant', 'teacher', 'professor', 'consultant', 'specialist',
            'tmj', 'occlusion', 'neuromuscular'
        ]
        
        for page in all_pages:
            text_lower = page['text'].lower()
            for keyword in profession_keywords:
                if keyword in text_lower:
                    # Find context around keyword
                    idx = text_lower.find(keyword)
                    if idx != -1:
                        start = max(0, idx - 50)
                        end = min(len(page['text']), idx + len(keyword) + 50)
                        evidence = page['text'][start:end].strip()
                        
                        # Extract profession phrase
                        context_start = max(0, idx - 30)
                        context_end = min(len(page['text']), idx + len(keyword) + 30)
                        profession_phrase = page['text'][context_start:context_end].strip()
                        
                        facts['profession'].append({
                            'value': profession_phrase,
                            'keyword': keyword,
                            'evidence': evidence,
                            'source_url': page['url']
                        })
        
        # 5. Experience years (pattern-based)
        exp_patterns = [
            re.compile(r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|in|practice|service)', re.I),
            re.compile(r'(?:experience|practicing|working)\s*(?:for|over|more than)?\s*(\d+)\+?\s*years?', re.I),
        ]
        for pattern in exp_patterns:
            for page in all_pages:
                exp_facts = self.extract_fact_with_evidence(pattern, page['text'])
                for fact in exp_facts:
                    years_match = re.search(r'\d+', fact['value'])
                    if years_match:
                        facts['experience_years'].append({
                            'value': int(years_match.group()),
                            'evidence': fact['evidence_snippet'],
                            'source_url': page['url']
                        })
        
        # 6. Location (keyword windows)
        location_keywords = ['based in', 'located in', 'from', 'lives in', 'address', 'clinic', 'practice']
        location_pattern = re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*(?:India|USA|UK|Delhi|Mumbai|Bangalore|Chennai|Kolkata|Hyderabad)', re.I)
        
        for page in all_pages:
            loc_facts = self.extract_fact_with_evidence(location_pattern, page['text'])
            for fact in loc_facts:
                facts['locations'].append({
                    'value': fact['value'],
                    'evidence': fact['evidence_snippet'],
                    'source_url': page['url']
                })
        
        # 7. Company/Clinic names (pattern-based)
        company_patterns = [
            re.compile(r'(?:at|with|founder of|CEO of|CTO of|works at|clinic|practice)\s+([A-Z][a-zA-Z0-9\s&]+(?:Inc|Ltd|LLC|Corp|Company|Clinic|Dental|Hospital)?)', re.I),
        ]
        for pattern in company_patterns:
            for page in all_pages:
                company_facts = self.extract_fact_with_evidence(pattern, page['text'])
                for fact in company_facts:
                    company_name = fact['value'].strip()
                    if len(company_name) > 3 and len(company_name) < 100:
                        facts['companies'].append({
                            'value': company_name,
                            'evidence': fact['evidence_snippet'],
                            'source_url': page['url']
                        })
        
        # 8. Bio snippets (sentences with person's name)
        name_variations = [person_name, person_name.split()[0], person_name.split()[-1] if ' ' in person_name else '']
        name_variations = [n for n in name_variations if n]
        
        for page in all_pages:
            sentences = re.split(r'[.!?]+', page['text'])
            for sentence in sentences:
                sentence = sentence.strip()
                if any(var.lower() in sentence.lower() for var in name_variations):
                    if 20 < len(sentence) < 500:
                        facts['bio_snippets'].append({
                            'value': sentence,
                            'evidence': sentence,
                            'source_url': page['url']
                        })
        
        # Deduplicate and limit
        for key in ['email', 'phone', 'websites']:
            if key in facts:
                seen = set()
                unique_facts = []
                for fact in facts[key]:
                    if fact['value'] not in seen:
                        seen.add(fact['value'])
                        unique_facts.append(fact)
                facts[key] = unique_facts[:5]  # Limit to 5
        
        return facts
    
    def calculate_confidence(self, fact_list: List[Dict]) -> Dict:
        """
        Calculate confidence scores and handle conflicts
        
        Returns:
            Dictionary with confidence-ranked facts
        """
        if not fact_list:
            return {'facts': [], 'confidence': 'low', 'needs_review': True}
        
        # Count occurrences
        value_counts = {}
        for fact in fact_list:
            value = fact['value']
            if value not in value_counts:
                value_counts[value] = {
                    'count': 0,
                    'sources': [],
                    'evidence': []
                }
            value_counts[value]['count'] += 1
            value_counts[value]['sources'].append(fact.get('source_url', ''))
            value_counts[value]['evidence'].append(fact.get('evidence', ''))
        
        # Sort by count (confidence)
        ranked = sorted(value_counts.items(), key=lambda x: x[1]['count'], reverse=True)
        
        # Determine confidence level
        if ranked[0][1]['count'] >= 3:
            confidence = 'high'
            needs_review = False
        elif ranked[0][1]['count'] >= 2:
            confidence = 'medium'
            needs_review = len(ranked) > 1  # Review if conflicts
        else:
            confidence = 'low'
            needs_review = True
        
        # Build result
        result = {
            'facts': [
                {
                    'value': value,
                    'count': data['count'],
                    'sources': data['sources'],
                    'evidence': data['evidence'][0]  # Best evidence
                }
                for value, data in ranked[:3]  # Top 3
            ],
            'confidence': confidence,
            'needs_review': needs_review
        }
        
        return result
    
    def build_about_table(self, facts: Dict) -> Dict:
        """Build structured About table with confidence scores"""
        
        # Process each fact type with confidence
        profession_conf = self.calculate_confidence(facts.get('profession', []))
        location_conf = self.calculate_confidence(facts.get('locations', []))
        company_conf = self.calculate_confidence(facts.get('companies', []))
        email_conf = self.calculate_confidence(facts.get('email', []))
        phone_conf = self.calculate_confidence(facts.get('phone', []))
        website_conf = self.calculate_confidence(facts.get('websites', []))
        exp_conf = self.calculate_confidence(facts.get('experience_years', []))
        
        # Get best values
        best_profession = profession_conf['facts'][0]['value'] if profession_conf['facts'] else 'Not specified'
        best_location = location_conf['facts'][0]['value'] if location_conf['facts'] else 'Not specified'
        best_company = company_conf['facts'][0]['value'] if company_conf['facts'] else 'Not specified'
        best_email = email_conf['facts'][0]['value'] if email_conf['facts'] else 'Not specified'
        best_phone = phone_conf['facts'][0]['value'] if phone_conf['facts'] else 'Not specified'
        best_website = website_conf['facts'][0]['value'] if website_conf['facts'] else 'Not specified'
        best_exp = exp_conf['facts'][0]['value'] if exp_conf['facts'] else None
        
        # Build bio from snippets
        bio_snippets = facts.get('bio_snippets', [])[:2]
        bio_text = ' '.join([s['value'] for s in bio_snippets]) if bio_snippets else 'Not available'
        
        about_table = {
            'Full Name': facts.get('full_name', ''),
            'Profession': best_profession,
            'Location': best_location,
            'Company/Clinic': best_company,
            'Experience': f"{best_exp} years" if best_exp else 'Not specified',
            'Websites': best_website,
            'Email': best_email,
            'Phone': best_phone,
            'Bio': bio_text,
        }
        
        # Add confidence metadata
        confidence_metadata = {
            'profession': profession_conf['confidence'],
            'location': location_conf['confidence'],
            'company': company_conf['confidence'],
            'email': email_conf['confidence'],
            'phone': phone_conf['confidence'],
            'website': website_conf['confidence'],
            'experience': exp_conf['confidence'],
        }
        
        return {
            'about_table': about_table,
            'confidence': confidence_metadata,
            'raw_facts': facts
        }
    
    def scrape_person(self, person_name: str, max_urls: int = 10) -> Dict:
        """Main method: Scrape public data and build About table"""
        
        # Step 1: Get user consent
        if not self.get_user_consent(person_name):
            return {'error': 'User did not provide consent'}
        
        print(f"\n🔍 Starting search for: {person_name}")
        
        # Step 2: Search Google CSE
        search_queries = [
            f'"{person_name}"',
            f'"{person_name}" professional profile',
        ]
        
        all_urls = []
        for query in search_queries:
            results = self.search_google_cse(query, max_results=5)
            all_urls.extend([r['url'] for r in results])
        
        # Deduplicate URLs
        unique_urls = list(dict.fromkeys(all_urls))[:max_urls]
        print(f"✓ Found {len(unique_urls)} unique URLs to scrape")
        
        # Step 3: Scrape URLs with identity filtering
        print(f"\n📄 Scraping {len(unique_urls)} URLs...")
        scraped_content = []
        for i, url in enumerate(unique_urls, 1):
            print(f"  [{i}/{len(unique_urls)}] Scraping: {url[:60]}...")
            content = self.scrape_url(url)
            
            if content:
                # Check identity fingerprint if provided
                if self.identity_fingerprint:
                    matches, match_count, matched_anchors = self.identity_fingerprint.matches(
                        url, content['text']
                    )
                    if not matches:
                        print(f"    ⊘ Rejected: Only {match_count} anchor matches (need {self.identity_fingerprint.required_matches})")
                        continue
                    else:
                        print(f"    ✓ Accepted: {match_count} anchor matches ({', '.join(matched_anchors)})")
                
                scraped_content.append(content)
            
            time.sleep(1)  # Rate limiting
        
        print(f"✓ Successfully scraped {len(scraped_content)} pages (after filtering)")
        
        if not scraped_content:
            return {'error': 'No valid pages found after filtering'}
        
        # Step 4: Extract facts with evidence
        print(f"\n🔎 Extracting facts with evidence...")
        facts = self.extract_facts(scraped_content, person_name)
        
        # Step 5: Build About table with confidence
        print(f"\n📋 Building About table with confidence scores...")
        result = self.build_about_table(facts)
        
        # Store full data
        self.scraped_data[person_name] = {
            **result,
            'scraped_urls': [c['url'] for c in scraped_content],
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return self.scraped_data[person_name]
    
    def save_results(self, person_name: str, output_file: str = None):
        """Save scraping results to JSON file"""
        if person_name not in self.scraped_data:
            print(f"No data found for {person_name}")
            return
        
        if output_file is None:
            output_file = f"about_{person_name.replace(' ', '_')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data[person_name], f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
    
    def print_about_table(self, person_name: str):
        """Print formatted About table"""
        if person_name not in self.scraped_data:
            print(f"No data found for {person_name}")
            return
        
        data = self.scraped_data[person_name]
        about_table = data['about_table']
        confidence = data.get('confidence', {})
        
        print(f"\n{'='*60}")
        print(f"ABOUT TABLE - {person_name.upper()}")
        print(f"{'='*60}\n")
        
        for key, value in about_table.items():
            if value and value != 'Not specified' and value != 'Not available':
                conf_level = confidence.get(key.lower().replace(' ', '_'), 'unknown')
                conf_icon = '✓' if conf_level == 'high' else '~' if conf_level == 'medium' else '?'
                print(f"{key:20} | {value} {conf_icon}")
        
        print(f"\n{'='*60}")
        print(f"Sources: {len(data['scraped_urls'])} URLs scraped")
        print(f"Timestamp: {data['timestamp']}")
        print(f"{'='*60}\n")
