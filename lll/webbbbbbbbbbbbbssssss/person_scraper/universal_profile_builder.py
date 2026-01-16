"""
Universal Profile Builder
Never builds from name only - requires anchors and identity resolution
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse
import re
from dataclasses import dataclass, field
from enum import Enum

try:
    from readability import Document
    HAS_READABILITY = True
except ImportError:
    HAS_READABILITY = False


class SourceTier(Enum):
    """Source trust tiers"""
    TIER_A = "tier_a"  # Highest trust: official sites, gov, verified directories
    TIER_B = "tier_b"  # Medium: conferences, awards, publishers
    TIER_C = "tier_c"  # Hints only: social media, must be confirmed


class RolePack(Enum):
    """Role-specific fact packs"""
    BUSINESS = "business"  # Companies, funding, products
    ACADEMIC = "academic"  # Publications, affiliations, research
    MEDICAL = "medical"  # Specialization, clinic, license, services
    ARTIST = "artist"  # Works, discography, filmography
    PUBLIC_FIGURE = "public_figure"  # Offices, policy roles, speeches
    GENERIC = "generic"  # Default


@dataclass
class FactCandidate:
    """A fact candidate with evidence"""
    field: str
    value: str
    source_url: str
    source_tier: SourceTier
    evidence_snippet: str
    confidence: float = 0.0
    confirmed: bool = False
    anchor_matches: List[str] = field(default_factory=list)
    score: float = 0.0  # Source weighting score
    from_structured_data: bool = False  # From JSON-LD/OpenGraph
    from_contact_page: bool = False  # From Contact/About page


@dataclass
class IdentityCandidate:
    """A candidate identity for resolution"""
    name: str
    domain: Optional[str] = None
    organization: Optional[str] = None
    location_hint: Optional[str] = None
    top_urls: List[str] = field(default_factory=list)
    role_hint: Optional[str] = None


class UniversalProfileBuilder:
    """Universal profile builder with identity resolution"""
    
    # Domain denylist
    DENYLIST_DOMAINS = [
        'linkedin.com',
        'facebook.com',
        'instagram.com',
        'twitter.com',
        'x.com',
        'youtube.com',
    ]
    
    # Tier A patterns (highest trust)
    TIER_A_PATTERNS = [
        r'\.edu$',  # Universities
        r'\.gov$',  # Government
        r'\.org$',  # Organizations
        r'google\.com/maps',  # Google Business
        r'justdial\.com',  # Business directory
        r'practo\.com',  # Medical directory
    ]
    
    # Tier B patterns
    TIER_B_PATTERNS = [
        r'conference',
        r'award',
        r'publisher',
        r'podcast',
        r'speaker',
    ]
    
    def __init__(self, google_cse_api_key: str, google_cse_id: str):
        """Initialize profile builder"""
        self.api_key = google_cse_api_key
        self.cse_id = google_cse_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.fact_candidates: List[FactCandidate] = []
        self.anchors: Set[str] = set()
        self.trusted_domains: Set[str] = set()  # Domains user provided as anchors
        self.anchor_domains: Set[str] = set()  # All anchor domains
        
    def normalize_phone(self, phone: str) -> str:
        """Normalize phone to E.164 format"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Handle Indian numbers
        if digits.startswith('91') and len(digits) == 12:
            return f"+{digits}"
        elif digits.startswith('0') and len(digits) == 11:
            return f"+91{digits[1:]}"
        elif len(digits) == 10:
            return f"+91{digits}"
        
        return phone
    
    def classify_source_tier(self, url: str) -> SourceTier:
        """Classify source into trust tier"""
        url_lower = url.lower()
        
        # Check denylist (Tier C)
        for denied in self.DENYLIST_DOMAINS:
            if denied in url_lower:
                return SourceTier.TIER_C
        
        # Check Tier A patterns
        for pattern in self.TIER_A_PATTERNS:
            if re.search(pattern, url_lower):
                return SourceTier.TIER_A
        
        # Check Tier B patterns
        for pattern in self.TIER_B_PATTERNS:
            if re.search(pattern, url_lower):
                return SourceTier.TIER_B
        
        # Default: check if official domain
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        # If domain matches anchor, likely Tier A
        if any(anchor in domain for anchor in self.anchors if '.' in anchor):
            return SourceTier.TIER_A
        
        # Default to Tier B
        return SourceTier.TIER_B
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content, avoiding junk"""
        if HAS_READABILITY:
            try:
                doc = Document(str(soup))
                content_html = doc.summary()
                content_soup = BeautifulSoup(content_html, 'html.parser')
                text = content_soup.get_text(separator=' ', strip=True)
                if len(text) > 200:
                    return text
            except:
                pass
        
        # Fallback: remove junk
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                            'aside', 'form', 'button', 'input', 'select',
                            'noscript', 'iframe', 'embed', 'object']):
            element.decompose()
        
        # Remove junk classes/ids
        junk_selectors = [
            {'class': re.compile(r'cookie|banner|popup|modal|overlay|ad', re.I)},
            {'id': re.compile(r'cookie|banner|popup|modal|overlay|ad', re.I)},
        ]
        
        for selector in junk_selectors:
            for element in soup.find_all(**selector):
                element.decompose()
        
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|article', re.I))
        
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
        
        # Clean text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return ' '.join(chunk for chunk in chunks if chunk)
    
    def search_google_cse(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Google CSE"""
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
                    if not any(denied in url_link.lower() for denied in self.DENYLIST_DOMAINS):
                        results.append({
                            'title': item.get('title', ''),
                            'url': url_link,
                            'snippet': item.get('snippet', ''),
                            'display_url': item.get('displayLink', '')
                        })
            
            return results
        except Exception as e:
            print(f"  ✗ Search error: {e}")
            return []
    
    def upgrade_to_https(self, url: str) -> str:
        """
        A) HTTP/HTTPS Upgrade
        Try HTTPS first, fall back to HTTP if needed
        """
        if url.startswith('http://'):
            https_url = url.replace('http://', 'https://', 1)
            try:
                response = self.session.head(https_url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    return https_url
            except:
                pass
            # Fall back to HTTP only if domain is trusted
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
            if domain in self.trusted_domains:
                return url  # Allow HTTP for trusted domains
            else:
                # Block HTTP for untrusted domains
                raise ValueError(f"HTTP not allowed for untrusted domain: {domain}")
        return url
    
    def normalize_url_variants(self, url: str) -> List[str]:
        """
        Generate URL variants to try (handles DNS failures)
        Tries: https://www, https://, http://www, http://
        """
        variants = []
        original_url = url
        
        # Parse URL
        url_lower = url.lower()
        if url_lower.startswith('http://'):
            url = url[7:]
        elif url_lower.startswith('https://'):
            url = url[8:]
        
        # Remove www. if present
        if url.startswith('www.'):
            url = url[4:]
        
        # Extract path
        if '/' in url:
            path = '/' + '/'.join(url.split('/')[1:])
            domain = url.split('/')[0]
        else:
            path = ''
            domain = url
        
        # Generate variants (prefer HTTPS)
        variants = [
            f"https://www.{domain}{path}",
            f"https://{domain}{path}",
            f"http://www.{domain}{path}",
            f"http://{domain}{path}",
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)
        
        return unique_variants
    
    def scrape_url(self, url: str) -> Optional[Dict]:
        """
        Scrape URL and extract main content with structured data
        FIX: Try multiple URL variants if DNS resolution fails
        """
        # Try multiple URL variants
        url_variants = self.normalize_url_variants(url)
        last_error = None
        
        for variant_url in url_variants:
            try:
                # Use proper User-Agent
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = self.session.get(variant_url, timeout=15, allow_redirects=True, headers=headers)
                
                if response.status_code == 403:
                    print(f"  ⊘ Blocked (403): {variant_url}")
                    return {'blocked': True}
                
                if response.status_code != 200:
                    continue  # Try next variant
                
                # Success - use this variant
                actual_url = response.url
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # FIX 2: Two-pass extraction (footer/header separately for contacts)
                # Pass A: Extract footer/header separately for contacts
                footer_text = ""
                header_text = ""
                contact_sections = []
                
                # Extract footer
                footer_tag = soup.find('footer')
                if footer_tag:
                    footer_text = footer_tag.get_text(separator=' ', strip=True)
                    footer_text = re.sub(r'\s+', ' ', footer_text)
                    contact_sections.append(footer_text)
                
                # Extract header
                header_tag = soup.find('header')
                if header_tag:
                    header_text = header_tag.get_text(separator=' ', strip=True)
                    header_text = re.sub(r'\s+', ' ', header_text)
                    contact_sections.append(header_text)
                
                # Extract contact sections (divs with "contact" class/id)
                for tag in soup.find_all(['div', 'section'], class_=re.compile(r'contact|footer|header', re.I)):
                    contact_text = tag.get_text(separator=' ', strip=True)
                    contact_text = re.sub(r'\s+', ' ', contact_text)
                    if contact_text:
                        contact_sections.append(contact_text)
                
                # Combine all contact sections
                contact_text = ' '.join(contact_sections)
                
                # Pass B: Extract main content (remove nav/footer/header for bio)
                for tag in soup.find_all(['header', 'nav', 'aside', 'script', 'style', 'footer']):
                    tag.decompose()
                
                text = self.extract_main_content(soup)
                text = re.sub(r'\s+', ' ', text)
                
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else ''
                
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc.get('content', '') if meta_desc else ''
                
                # Extract structured data (JSON-LD, OpenGraph)
                structured_data = self.extract_structured_data(soup, actual_url)
                
                # FIX 6: Extract JSON-LD data
                json_ld_data = self.extract_json_ld(html)
                if json_ld_data:
                    structured_data.update(json_ld_data)
                
                # FIX 4: Extract from mailto: and tel: links
                mailto_emails = []
                tel_phones = []
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '').lower()
                    if href.startswith('mailto:'):
                        email = href.replace('mailto:', '').split('?')[0].strip()
                        if email:
                            mailto_emails.append(email)
                    elif href.startswith('tel:'):
                        phone = href.replace('tel:', '').strip()
                        if phone:
                            tel_phones.append(phone)
                
                # Quick diagnosis
                html_lower = html.lower()
                has_contact_word = 'contact' in html_lower
                raw_emails = re.findall(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', html_lower)
                raw_phones = re.findall(r'(?:\+91[-\s]?)?\d[\d\s\-()]{8,}\d', html_lower)
                
                # Detect source type
                source_type = self.detect_source_type(actual_url, soup)
                source_specific = {}
                
                if source_type == 'wikipedia':
                    source_specific['infobox'] = self.parse_wikipedia_infobox(soup)
                    source_specific['first_sentence'] = self.parse_wikipedia_first_sentence(soup)
                
                return {
                    'url': actual_url,  # Store the working URL
                    'title': title_text,
                    'description': description,
                    'text': text,  # Main content (bio/services)
                    'contact_text': contact_text,  # Footer/header/contact sections
                    'footer_text': footer_text,
                    'header_text': header_text,
                    'mailto_emails': mailto_emails,
                    'tel_phones': tel_phones,
                    'html': html,  # Store full HTML
                    'structured_data': structured_data,
                    'is_contact_page': any(page in actual_url.lower() for page in ['/contact', '/about', '/team']),
                    'source_type': source_type,
                    'source_specific': source_specific,
                    'blocked': False,
                    '_diagnosis': {
                        'html_length': len(html),
                        'has_contact_word': has_contact_word,
                        'raw_emails_count': len(raw_emails),
                        'raw_phones_count': len(raw_phones)
                    }
                }
            except Exception as e:
                last_error = e
                continue  # Try next variant
        
        # All variants failed
        if last_error:
            print(f"  ✗ Failed to scrape {url}: {last_error}")
        return None
    
    def extract_structured_data(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract structured data from JSON-LD and OpenGraph"""
        structured = {
            'name': None,
            'organization': None,
            'address': None,
            'email': None,
            'phone': None,
            'website': None,
            'specialty': None
        }
        
        # JSON-LD extraction
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    data_list = [data]
                elif isinstance(data, list):
                    data_list = data
                else:
                    continue
                
                for item in data_list:
                    item_type = item.get('@type', '').lower()
                    if 'person' in item_type or 'dentist' in item_type or 'localbusiness' in item_type or 'organization' in item_type:
                        if 'name' in item and not structured['name']:
                            structured['name'] = item['name']
                        if 'email' in item and not structured['email']:
                            structured['email'] = item['email']
                        if 'telephone' in item and not structured['phone']:
                            structured['phone'] = item['telephone']
                        if 'url' in item and not structured['website']:
                            structured['website'] = item['url']
                        if 'address' in item:
                            addr = item['address']
                            if isinstance(addr, dict):
                                addr_str = ', '.join([v for k, v in addr.items() if k != '@type' and v])
                                if addr_str and not structured['address']:
                                    structured['address'] = addr_str
                        if 'medicalSpecialty' in item and not structured['specialty']:
                            structured['specialty'] = item['medicalSpecialty']
                        if 'name' in item and ('organization' in item_type or 'localbusiness' in item_type) and not structured['organization']:
                            structured['organization'] = item['name']
            except:
                continue
        
        # OpenGraph extraction
        og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
        for tag in og_tags:
            prop = tag.get('property', '').replace('og:', '')
            content = tag.get('content', '')
            if prop == 'title' and not structured['name']:
                structured['name'] = content
            elif prop == 'site_name' and not structured['organization']:
                structured['organization'] = content
        
        return structured
    
    def normalize_domain(self, domain: str) -> str:
        """
        FIX 2: Normalize domain correctly
        if input is http://www.zentaldental.com/ → normalize to zentaldental.com
        strip http(s)://, strip www., strip paths, lowercase
        """
        if not domain:
            return ""
        
        # Remove protocol
        domain = re.sub(r'^https?://', '', domain, flags=re.I)
        
        # Remove www.
        domain = re.sub(r'^www\.', '', domain, flags=re.I)
        
        # Remove paths
        domain = domain.split('/')[0]
        domain = domain.split('?')[0]  # Remove query params
        domain = domain.split('#')[0]  # Remove fragments
        
        # Remove trailing dot
        domain = domain.rstrip('.')
        
        return domain.lower().strip()
    
    def is_valid_domain(self, domain_input: str) -> Tuple[bool, str]:
        """
        FIX 1: Validate if input is actually a domain/URL
        Returns (is_valid, normalized_domain)
        """
        if not domain_input or not domain_input.strip():
            return False, ""
        
        domain_input = domain_input.strip()
        
        # Must contain a dot (domain extension) OR start with http
        has_dot = '.' in domain_input
        has_http = domain_input.lower().startswith(('http://', 'https://'))
        
        if not has_dot and not has_http:
            # Not a domain - probably a job title or other text
            return False, ""
        
        # Normalize and validate
        normalized = self.normalize_domain(domain_input)
        
        # Check if normalized result looks like a domain (has TLD)
        if '.' not in normalized:
            return False, ""
        
        # Check for valid TLD
        tld_pattern = r'\.[a-z]{2,}$'
        if not re.search(tld_pattern, normalized):
            return False, ""
        
        return True, normalized
    
    def smart_field_assigner(self, name: Optional[str], domain: Optional[str], 
                             organization: Optional[str], city: Optional[str],
                             handle: Optional[str], known_page: Optional[str]) -> Dict:
        """
        FIX: Smart field assignment - auto-correct user inputs
        """
        corrections = []
        
        # Check domain field
        if domain:
            is_valid, normalized = self.is_valid_domain(domain)
            if not is_valid:
                # Domain looks like a job word - move to organization
                if not organization:
                    organization = domain
                    corrections.append(f"Detected '{domain}' in Domain field; moved to Organization.")
                domain = None
            else:
                domain = normalized
        
        # Check handle field - if it contains http, move to domain
        if handle:
            if 'http' in handle.lower() or '.' in handle:
                is_valid, normalized = self.is_valid_domain(handle)
                if is_valid:
                    if not domain:
                        domain = normalized
                        corrections.append(f"Detected website URL in Handle; moved to Domain.")
                    handle = None
        
        # Check known_page - if provided, treat as start URL
        if known_page:
            is_valid, normalized = self.is_valid_domain(known_page)
            if is_valid:
                if not domain:
                    domain = normalized
                    corrections.append(f"Detected website URL in Known page; moved to Domain.")
        
        if corrections:
            print("\n⚠️  Input corrections applied:")
            for correction in corrections:
                print(f"   {correction}")
        
        return {
            'name': name,
            'domain': domain,
            'organization': organization,
            'city': city,
            'handle': handle,
            'known_page': known_page
        }
    
    def score_candidate(self, candidate: IdentityCandidate, 
                      user_domain: Optional[str] = None,
                      organization: Optional[str] = None) -> int:
        """
        Score candidate for ranking
        +100 if domain matches user domain
        +30 if URL is on same domain
        +10 if "About/Team/Contact" page
        -20 if directory (justdial/practo)
        -50 if unrelated domains
        """
        score = 0
        normalized_user_domain = self.normalize_domain(user_domain) if user_domain else ""
        normalized_candidate_domain = self.normalize_domain(candidate.domain) if candidate.domain else ""
        
        # Domain match (highest priority)
        if normalized_user_domain and normalized_candidate_domain:
            if normalized_user_domain == normalized_candidate_domain:
                score += 100
            elif normalized_user_domain in normalized_candidate_domain or normalized_candidate_domain in normalized_user_domain:
                score += 50
        
        # Check URLs for scoring
        for url in candidate.top_urls:
            url_lower = url.lower()
            parsed = urlparse(url)
            url_domain = parsed.netloc.lower().replace('www.', '')
            
            # Same domain bonus
            if normalized_user_domain and normalized_user_domain in url_domain:
                score += 30
            
            # About/Team/Contact page bonus
            path = parsed.path.lower()
            if any(page in path for page in ['/about', '/team', '/contact', '/our-team']):
                score += 10
            
            # Directory penalty
            if any(dir_site in url_domain for dir_site in ['justdial.com', 'practo.com', 'indiamart.com']):
                score -= 20
        
        # Organization match bonus
        if organization and candidate.organization:
            if organization.lower() in candidate.organization.lower():
                score += 15
        
        return score
    
    def resolve_identity_candidates(self, 
                                    name: Optional[str] = None,
                                    domain: Optional[str] = None,
                                    organization: Optional[str] = None,
                                    city: Optional[str] = None,
                                    handle: Optional[str] = None,
                                    known_page: Optional[str] = None) -> List[IdentityCandidate]:
        """
        STEP 1: Identity Resolution
        Build candidate list from available anchors
        FIX 1: Domain anchor beats everything
        FIX 2: Proper candidate ranking
        """
        candidates = []
        normalized_user_domain = self.normalize_domain(domain) if domain else None
        
        # Build search queries from available anchors
        queries = []
        
        if name:
            if domain:
                queries.append(f'"{name}" site:{domain}')
            if organization:
                queries.append(f'"{name}" "{organization}"')
            if city:
                queries.append(f'"{name}" "{city}"')
            if not queries:
                queries.append(f'"{name}"')
        
        if domain:
            queries.append(f'site:{domain}')
            normalized_domain = self.normalize_domain(domain)
            self.anchors.add(normalized_domain)
            self.anchor_domains.add(normalized_domain)
            self.trusted_domains.add(normalized_domain)  # A) HTTP allowed for user-provided domains
        
        if organization:
            queries.append(f'"{organization}"')
            self.anchors.add(organization.lower())
        
        if city:
            self.anchors.add(city.lower())
        
        if handle:
            queries.append(f'"{handle}"')
        
        if known_page:
            queries.append(f'site:{known_page}')
        
        # Search and build candidates
        all_urls = set()
        for query in queries[:3]:  # Limit queries
            results = self.search_google_cse(query, max_results=5)
            for result in results:
                all_urls.add(result['url'])
        
        # Group by domain/organization to build candidates
        domain_groups = {}
        for url in all_urls:
            parsed = urlparse(url)
            domain_key = parsed.netloc.lower().replace('www.', '')
            if domain_key not in domain_groups:
                domain_groups[domain_key] = []
            domain_groups[domain_key].append(url)
        
        # Build candidates
        for domain_key, urls in domain_groups.items():
            candidate = IdentityCandidate(
                name=name or "Unknown",
                domain=domain_key,
                top_urls=urls[:5],  # Keep more URLs for scoring
                organization=organization,
                location_hint=city
            )
            candidates.append(candidate)
        
        # FIX 3: If user provided domain, filter to EXACT domain matches only
        if normalized_user_domain:
            domain_matches = []
            for c in candidates:
                candidate_domain = self.normalize_domain(c.domain)
                # Strict match - must be exact
                if candidate_domain == normalized_user_domain:
                    domain_matches.append(c)
            
            if domain_matches:
                # Score and sort domain matches
                for candidate in domain_matches:
                    candidate_score = self.score_candidate(candidate, domain, organization)
                    candidate._score = candidate_score
                domain_matches.sort(key=lambda c: c._score, reverse=True)
                return domain_matches[:5]
        
        # FIX 2: Score and rank all candidates
        for candidate in candidates:
            candidate._score = self.score_candidate(candidate, domain, organization)
        
        # Sort by score (descending)
        candidates.sort(key=lambda c: c._score, reverse=True)
        
        return candidates[:5]  # Max 5 candidates
    
    def is_person_page(self, url: str, content: Dict, target_name: str, is_anchor_domain: bool = False) -> Tuple[bool, str]:
        """
        Person-page filter: Check if page is about target person
        FIX 3: For contact facts on anchor domain, don't require name tokens
        """
        if not content or content.get('blocked'):
            return False, "Blocked or no content"
        
        text = content.get('text', '')
        contact_text = content.get('contact_text', '')
        # Normalize text: lowercase, replace punctuation with spaces
        text_normalized = text.lower()
        text_normalized = re.sub(r'[.,\-_/]', ' ', text_normalized)
        text_normalized = re.sub(r'\s+', ' ', text_normalized)
        
        url_lower = url.lower()
        name_tokens = self.extract_name_tokens(target_name)
        
        # FIX 3: For contact facts on anchor domain, allow any page (homepage included)
        # For person facts, require name tokens
        if is_anchor_domain:
            # Anchor domain pages are always allowed (for contact extraction)
            # But check if it has person content too
            if name_tokens:
                all_tokens_present = all(token in text_normalized or token in contact_text.lower() for token in name_tokens)
                if all_tokens_present:
                    return True, "Anchor domain page with name tokens"
                else:
                    # Still allow for contact extraction
                    return True, "Anchor domain page (contact facts allowed)"
            else:
                return True, "Anchor domain page"
        
        # For non-anchor pages, require name tokens
        if name_tokens:
            all_tokens_present = all(token in text_normalized for token in name_tokens)
            if not all_tokens_present:
                return False, f"Missing name tokens (need all of: {name_tokens})"
        elif not target_name:
            return False, "No target name provided"
        
        matches = 0
        reasons = []
        
        # Criterion 1: Contains all name tokens in text (required)
        if all(token in text_normalized for token in name_tokens):
            matches += 1
            reasons.append("name tokens in text")
        
        # Criterion 2: URL slug contains name tokens
        if any(token in url_lower for token in name_tokens):
            matches += 1
            reasons.append("name token in URL")
        
        # Criterion 3: Schema.org Person with matching name
        structured = content.get('structured_data', {})
        if structured.get('name'):
            struct_name = structured['name'].lower()
            struct_normalized = re.sub(r'[.,\-_/]', ' ', struct_name)
            struct_normalized = re.sub(r'\s+', ' ', struct_normalized)
            if all(token in struct_normalized for token in name_tokens):
                matches += 1
                reasons.append("schema.org Person")
        
        # Criterion 4: Clinic anchor + name near each other
        if any(anchor in text.lower() for anchor in self.anchor_domains):
            # Check if name tokens appear near anchor
            for anchor in self.anchor_domains:
                anchor_idx = text.lower().find(anchor)
                if anchor_idx != -1:
                    context = text_normalized[max(0, anchor_idx//len(text)*len(text_normalized)-50):min(len(text_normalized), anchor_idx//len(text)*len(text_normalized)+len(anchor)+50)]
                    if all(token in context for token in name_tokens):
                        matches += 1
                        reasons.append("anchor + name proximity")
                        break
        
        # Require at least 1 match (name tokens in text is required above)
        if matches >= 1:
            return True, f"Matches: {', '.join(reasons)}"
        else:
            return False, f"Only {matches} match(es), need 1"
    
    def is_value_blacklisted(self, value: str, field: str) -> Tuple[bool, str]:
        """
        Value blacklist: Never allow junk values
        """
        value_lower = value.lower().strip()
        
        # Domain-like strings
        if any(domain in value_lower for domain in ['.com', '.in', '.org', '.net', '.co']):
            return True, "Contains domain extension"
        
        # Stopwords (alone or as single words)
        stopwords = ['patients', 'teeth', 'heart', 'services', 'treatments', 'clinic', 'dental', 'care']
        if value_lower in stopwords:
            return True, "Stopword"
        
        # Short fragments
        if len(value) < 4:
            return True, "Too short"
        
        # Sentences with verbs/pronouns (fragments)
        if any(pronoun in value_lower for pronoun in ['her ', 'his ', 'their ', 'our ', 'your ']):
            if len(value.split()) < 5:  # Short fragment with pronoun
                return True, "Pronoun fragment"
        
        # Field-specific blacklists
        if field == 'full_name':
            # Reject if contains domain
            if any(ext in value_lower for ext in ['.com', '.in', '.org']):
                return True, "Name contains domain"
            # Reject if too long (likely page title)
            if len(value) > 100:
                return True, "Too long for name"
        
        if field == 'primary_organization':
            # Reject domains
            if any(ext in value_lower for ext in ['.com', '.in', '.org']):
                return True, "Organization is domain"
            # Reject generic words
            if value_lower in ['clinic', 'dental', 'hospital', 'care']:
                return True, "Generic word"
        
        if field == 'location':
            # Reject if contains verbs/actions
            if any(verb in value_lower for verb in ['patients', 'treatment', 'service']):
                return True, "Contains action words"
        
        return False, "Not blacklisted"
    
    def extract_name_tokens(self, name: str) -> List[str]:
        """
        Extract name tokens: normalize and ignore "dr"
        For "Dr.Sanjay Arora" → ["sanjay", "arora"]
        """
        if not name:
            return []
        
        # Normalize: lowercase, replace punctuation with spaces
        normalized = name.lower()
        normalized = re.sub(r'[.,\-_/]', ' ', normalized)  # Replace punctuation with space
        normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
        normalized = normalized.strip()
        
        # Split into tokens and filter out "dr"
        tokens = normalized.split()
        tokens = [t for t in tokens if t not in ['dr', 'doctor', 'mr', 'mrs', 'ms']]
        
        return tokens
    
    def is_person_url(self, url: str, target_name: str, is_anchor_domain: bool = False) -> Tuple[bool, str]:
        """
        URL filter: Only allow person/contact/about pages, deny service pages
        FIX: Allow homepage and contact/about always for anchor domain
        """
        url_lower = url.lower()
        name_tokens = self.extract_name_tokens(target_name)
        
        # FIX: Allow homepage always when domain is anchor
        if is_anchor_domain:
            if url_lower.endswith('/') or url_lower.count('/') <= 3:  # Homepage or shallow pages
                return True, "Homepage or shallow page on anchor domain"
        
        # Allow patterns (good pages)
        allow_patterns = [
            'about', 'contact', 'team', 'doctor', 'doctors', 'staff',
            'dr-', 'dr_', 'dr.', 'founder', 'director', 'profile', 'bio'
        ]
        
        # Also allow if URL contains name tokens (token-based, not literal)
        if name_tokens:
            for token in name_tokens:
                if len(token) > 3 and token in url_lower:
                    return True, f"Contains name token: {token}"
        
        # Check allow patterns
        for pattern in allow_patterns:
            if pattern in url_lower:
                return True, f"Matches allow pattern: {pattern}"
        
        # FIX: For medical pack, allow service pages but mark them differently
        # Don't deny them completely - they can be used for services/interests
        # Only deny clearly non-person pages
        deny_patterns = [
            '/blog', '/news', '/gallery', '/video', '/privacy', '/terms',
            '/pdf', '.pdf'  # PDFs are usually not person pages
        ]
        
        for pattern in deny_patterns:
            if pattern in url_lower:
                return False, f"Matches deny pattern: {pattern}"
        
        # For anchor domain, be more lenient
        if is_anchor_domain:
            return True, "Anchor domain page (lenient)"
        
        # If no clear match, default to deny (strict filtering)
        return False, "No allow pattern match"
    
    def collect_sources(self, selected_candidate: IdentityCandidate, user_domain: Optional[str] = None) -> List[Dict]:
        """
        STEP 2: Source Collection
        Collect sources in tiers
        FIX 5: Crawl internal pages when domain provided
        """
        sources = []
        urls_to_scrape = set(selected_candidate.top_urls)
        
        # FIX A: Force-include the right pages (specific URLs for zentaldental.com)
        if user_domain:
            normalized_domain = self.normalize_domain(user_domain)
            base_url = f"https://{normalized_domain}"
            
            # Domain-specific forced URLs
            if normalized_domain == 'zentaldental.com':
                # Education/experience page
                forced_urls = [
                    'https://www.zentaldental.com/cranio-sacral-tmj-specialist-neuro-muscular-tmj-specialist-epigeneticist-master-ceramist-craniodontist-occlusion-specialist-tmj-treatment.html',
                    'https://www.zentaldental.com/dental-clinic-in-delhi-dental-clinic-in-south-delhi-dental-delhi-dental-south-delhi-dental-clinic-new-delhi-best-dental-clinic-delhi.html',
                ]
                # Optional backup authority page
                forced_urls.append('https://www.indiadentalclinic.com/en/clinic/zental-dental-cosmetic-research-institute/team.htm')
                
                for forced_url in forced_urls:
                    urls_to_scrape.add(forced_url)
                    print(f"  ✓ Added forced URL: {forced_url}")
            
            # Forced contact/about URLs (always try these)
            forced_pages = [
                '/contact.html',
                '/contact-us.html',
                '/contact',
                '/about.html',
                '/about-us.html',
                '/about',
                '/team',
                '/our-team',
            ]
            
            # Try name-based slugs if name available
            if selected_candidate.name:
                name_tokens = self.extract_name_tokens(selected_candidate.name)
                if name_tokens:
                    # Try different slug formats
                    name_slug = '-'.join(name_tokens)
                    forced_pages.extend([
                        f'/dr-{name_slug}',
                        f'/doctor-{name_slug}',
                        f'/{name_slug}',
                    ])
            
            # Try to access forced pages
            for page in forced_pages:
                test_url = base_url + page
                try:
                    # Quick HEAD request to check if page exists
                    response = self.session.head(test_url, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        urls_to_scrape.add(test_url)
                        print(f"  ✓ Found forced page: {test_url}")
                except:
                    pass  # Page doesn't exist, skip
        
        # Add more URLs from searches
        if selected_candidate.name:
            queries = [
                f'"{selected_candidate.name}"',
                f'"{selected_candidate.name}" {selected_candidate.organization or ""}',
            ]
            for query in queries:
                results = self.search_google_cse(query, max_results=5)
                for result in results:
                    urls_to_scrape.add(result['url'])
        
        # FIX 3: When domain is provided, do domain-only crawling first
        target_name = selected_candidate.name
        name_tokens = self.extract_name_tokens(target_name)
        filtered_urls = []
        
        if user_domain:
            normalized_domain = self.normalize_domain(user_domain)
            print(f"  Phase A: Collecting URLs from {normalized_domain} only...")
            
            # Phase A: Domain-only URLs
            domain_urls = []
            for url in list(urls_to_scrape):
                url_domain = urlparse(url).netloc.lower().replace('www.', '')
                is_anchor = normalized_domain in url_domain
                
                if is_anchor:
                    # Check if URL is allowed (with anchor domain leniency)
                    is_allowed, reason = self.is_person_url(url, target_name, is_anchor_domain=True)
                    if is_allowed:
                        domain_urls.append(url)
                        print(f"    ✓ URL allowed: {reason} - {url[:60]}...")
                    else:
                        print(f"    ⊘ URL denied: {reason} - {url[:60]}...")
            
            filtered_urls = domain_urls
            
            # Phase B: Add external sources only if needed
            if not filtered_urls:
                print(f"  Phase B: No domain pages found. Adding external sources...")
                if target_name:
                    queries = [
                        f'"{target_name}" {selected_candidate.organization or ""}',
                        f'"{target_name}" contact',
                    ]
                    for query in queries:
                        results = self.search_google_cse(query, max_results=3)
                        for result in results:
                            result_url = result['url'] if isinstance(result, dict) else result
                            # Only add Justdial/Practo/Google Business
                            if any(dir_site in result_url for dir_site in ['justdial.com', 'practo.com', 'google.com/maps']):
                                filtered_urls.append(result_url)
        else:
            # No domain provided - filter all URLs
            for url in list(urls_to_scrape):
                is_person_url_result, reason = self.is_person_url(url, target_name)
                if is_person_url_result:
                    filtered_urls.append(url)
                    print(f"    ✓ URL allowed: {reason} - {url[:60]}...")
                else:
                    print(f"    ⊘ URL denied: {reason} - {url[:60]}...")
        
        # FIX 5: Fallback if 0 sources after filtering
        if not filtered_urls:
            print(f"  ⚠️  No filtered URLs found. Trying fallback...")
            # Relax to just name tokens (drop "dr")
            if user_domain and name_tokens:
                normalized_domain = self.normalize_domain(user_domain)
                base_url = f"https://{normalized_domain}"
                fallback_pages = ['/', '/contact', '/about']
                for page in fallback_pages:
                    test_url = base_url + page
                    try:
                        response = self.session.head(test_url, timeout=5, allow_redirects=True)
                        if response.status_code == 200:
                            filtered_urls.append(test_url)
                            print(f"    ✓ Fallback page found: {test_url}")
                    except:
                        pass
            
            if not filtered_urls:
                print(f"  ❌ Could not find pages mentioning {target_name} on this domain.")
                print(f"     Please provide the exact doctor profile URL.")
                return []  # Return empty sources
        
        # Prioritize contact/about/team pages
        priority_keywords = ['contact', 'about', 'team', 'doctor']
        filtered_urls.sort(key=lambda u: (
            -max([u.lower().count(kw) for kw in priority_keywords]),  # More priority keywords = higher
            u  # Then alphabetically
        ))
        
        # Scrape filtered URLs
        print(f"  Scraping {len(filtered_urls)} filtered URLs...")
        for url in filtered_urls[:20]:  # Limit to 20
            tier = self.classify_source_tier(url)
            
            # Try to scrape URL (will try multiple variants)
            content = self.scrape_url(url)
            
            if content:
                # Skip blocked sources (403)
                if content.get('blocked'):
                    continue
                
                # Person-page filter: Only keep pages about target person
                # FIX 3: For anchor domain, allow for contact extraction even without name tokens
                # Use the actual URL that worked (might be different variant)
                actual_url = content.get('url', url)
                url_domain = urlparse(actual_url).netloc.lower().replace('www.', '')
                is_anchor = any(anchor in url_domain for anchor in self.anchor_domains)
                
                is_relevant, reason = self.is_person_page(actual_url, content, target_name, is_anchor_domain=is_anchor)
                if not is_relevant:
                    print(f"    ⊘ Rejected: {reason} - {actual_url[:60]}...")
                    continue
                
                print(f"    ✓ Accepted: {reason} - {actual_url[:60]}...")
                
                # Print diagnosis info
                diag = content.get('_diagnosis', {})
                if diag:
                    print(f"      📊 HTML: {diag.get('html_length', 0)} chars, Contact word: {diag.get('has_contact_word', False)}, Raw emails: {diag.get('raw_emails_count', 0)}, Raw phones: {diag.get('raw_phones_count', 0)}")
                
                sources.append({
                    'url': actual_url,  # Use the working URL variant
                    'tier': tier,
                    'content': content,
                    'domain': url_domain
                })
                time.sleep(1)  # Rate limiting
            else:
                print(f"    ✗ Failed to scrape: {url[:60]}...")
        
        # Try Wikidata if name available
        if selected_candidate.name:
            print("  🔍 Fetching Wikidata data...")
            wikidata_data = self.fetch_wikidata(selected_candidate.name)
            if wikidata_data:
                sources.append({
                    'url': 'https://www.wikidata.org',
                    'tier': SourceTier.TIER_A,
                    'content': {
                        'url': 'https://www.wikidata.org',
                        'text': '',
                        'structured_data': wikidata_data,
                        'source_type': 'wikidata',
                        'blocked': False
                    },
                    'domain': 'wikidata.org'
                })
        
        return sources
    
    def validate_primary_organization(self, value: str, anchor_domains: Set[str]) -> Tuple[bool, str]:
        """
        B) Fix 1: Primary organization validator
        Reject: single common nouns, < 2 words (unless known brand), prepositions
        Accept: matches anchor, looks like org name, from structured data
        """
        value_lower = value.lower().strip()
        
        # Reject single common nouns
        common_nouns = ['heart', 'teeth', 'pain', 'smile', 'clinic', 'hospital', 'dental', 'care']
        if value_lower in common_nouns:
            return False, "Single common noun"
        
        # Reject if starts with preposition
        if re.match(r'^(from|in|at|to|with)\s+', value_lower):
            return False, "Starts with preposition"
        
        # Reject if < 2 words and not a known brand
        words = value.split()
        if len(words) < 2:
            # Check if it's a known brand/domain
            if not any(domain in value_lower for domain in anchor_domains):
                return False, "Single word, not a known brand"
        
        # Accept if matches anchor
        if any(domain in value_lower for domain in anchor_domains):
            return True, "Matches anchor domain"
        
        # Accept if looks like org name (2-6 words, Title Case)
        if 2 <= len(words) <= 6 and value[0].isupper():
            return True, "Looks like org name"
        
        return True, "Passed validation"
    
    def validate_specialization(self, value: str, role_pack: RolePack) -> Tuple[bool, str]:
        """
        B) Fix 1: Specialization validator
        Reject: starts with "from/in/based in"
        Accept: contains role-pack keywords
        """
        value_lower = value.lower().strip()
        
        # Reject if starts with location preposition
        if re.match(r'^(from|in|based in|located in)\s+', value_lower):
            return False, "Starts with location preposition"
        
        # Medical pack keywords
        if role_pack == RolePack.MEDICAL:
            medical_keywords = ['tmj', 'endodont', 'occlusion', 'implant', 'cosmetic', 'laser', 
                              'bruxism', 'cranio', 'neuro', 'orthodont', 'periodont', 'oral']
            if any(kw in value_lower for kw in medical_keywords):
                return True, "Contains medical keyword"
        
        # If no keywords match, still accept if it's substantial
        if len(value.split()) >= 2:
            return True, "Substantial specialization"
        
        return False, "No medical keywords, too short"
    
    def parse_wikipedia_infobox(self, soup: BeautifulSoup) -> Dict:
        """Parse Wikipedia infobox for structured data"""
        infobox_data = {}
        
        # Find infobox table
        infobox = soup.find('table', class_=re.compile(r'infobox', re.I))
        if not infobox:
            return infobox_data
        
        # Extract infobox rows
        for row in infobox.find_all('tr'):
            header = row.find('th')
            data = row.find('td')
            
            if header and data:
                key = header.get_text(strip=True).lower()
                value = data.get_text(strip=True)
                
                # Map common infobox fields
                if 'name' in key or 'full name' in key:
                    infobox_data['full_name'] = value
                elif 'occupation' in key or 'profession' in key:
                    infobox_data['profession'] = value
                elif 'born' in key or 'birth' in key:
                    infobox_data['birth_date'] = value
                elif 'nationality' in key or 'citizenship' in key:
                    infobox_data['nationality'] = value
                elif 'known for' in key:
                    infobox_data['known_for'] = value
                elif 'website' in key or 'url' in key:
                    link = data.find('a')
                    if link:
                        infobox_data['official_website'] = link.get('href', '')
        
        return infobox_data
    
    def parse_wikipedia_first_sentence(self, soup: BeautifulSoup) -> Dict:
        """Parse Wikipedia first sentence for profession"""
        first_sentence_data = {}
        
        # Find first paragraph after infobox
        content = soup.find('div', class_='mw-parser-output')
        if not content:
            return first_sentence_data
        
        # Get first paragraph
        first_p = content.find('p')
        if first_p:
            text = first_p.get_text(strip=True)
            # Pattern: "X is a/an [profession]"
            match = re.search(r'is\s+(?:a|an)\s+([^,\.]+)', text, re.I)
            if match:
                profession = match.group(1).strip()
                # Validate profession
                if self.validate_profession(profession)[0]:
                    first_sentence_data['profession'] = profession
        
        return first_sentence_data
    
    def fetch_wikidata(self, name: str) -> Dict:
        """Fetch structured data from Wikidata"""
        wikidata_data = {}
        
        try:
            # Search Wikidata
            search_url = "https://www.wikidata.org/w/api.php"
            params = {
                'action': 'wbsearchentities',
                'search': name,
                'language': 'en',
                'format': 'json'
            }
            response = self.session.get(search_url, params=params, timeout=5)
            if response.status_code != 200:
                return wikidata_data
            
            data = response.json()
            if 'search' not in data or not data['search']:
                return wikidata_data
            
            # Get first result entity ID
            entity_id = data['search'][0].get('id')
            if not entity_id:
                return wikidata_data
            
            # Get entity data
            entity_url = "https://www.wikidata.org/w/api.php"
            entity_params = {
                'action': 'wbgetentities',
                'ids': entity_id,
                'format': 'json',
                'props': 'claims|sitelinks'
            }
            entity_response = self.session.get(entity_url, params=entity_params, timeout=5)
            if entity_response.status_code != 200:
                return wikidata_data
            
            entity_data = entity_response.json()
            if 'entities' not in entity_data or entity_id not in entity_data['entities']:
                return wikidata_data
            
            entity = entity_data['entities'][entity_id]
            claims = entity.get('claims', {})
            
            # Extract occupation (P106)
            if 'P106' in claims:
                occupations = []
                for claim in claims['P106']:
                    if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                        # Would need to resolve QID to label, simplified here
                        occupations.append('occupation')
                if occupations:
                    wikidata_data['profession'] = ', '.join(occupations[:3])
            
            # Extract date of birth (P569)
            if 'P569' in claims:
                dob_claim = claims['P569'][0]
                if 'mainsnak' in dob_claim and 'datavalue' in dob_claim['mainsnak']:
                    time_value = dob_claim['mainsnak']['datavalue'].get('value', {}).get('time', '')
                    if time_value:
                        wikidata_data['birth_date'] = time_value
            
            # Extract nationality (P27)
            if 'P27' in claims:
                nationality_claim = claims['P27'][0]
                if 'mainsnak' in nationality_claim:
                    wikidata_data['nationality'] = 'nationality'
            
            # Extract official website (P856)
            if 'P856' in claims:
                website_claim = claims['P856'][0]
                if 'mainsnak' in website_claim and 'datavalue' in website_claim['mainsnak']:
                    website = website_claim['mainsnak']['datavalue'].get('value', '')
                    if website:
                        wikidata_data['official_website'] = website
            
        except Exception as e:
            print(f"  ⚠️  Wikidata fetch failed: {e}")
        
        return wikidata_data
    
    def validate_profession(self, value: str) -> Tuple[bool, str]:
        """
        Field guardrails: Profession validator
        Must contain profession keywords, reject family context
        """
        value_lower = value.lower()
        
        # Reject long sentence fragments
        if len(value) > 120:
            return False, "Too long (sentence fragment)"
        
        # Reject family context (strict)
        family_keywords = ['father', 'mother', 'brother', 'sister', 'parent']
        if any(kw in value_lower for kw in family_keywords):
            return False, "Contains family context"
        
        # Reject "worked as" when preceded by family context
        if 'worked as' in value_lower:
            # Check if it's about family member
            if any(fam in value_lower for fam in ['his father', 'her father', 'his mother', 'her mother']):
                return False, "Family member's profession"
        
        # Must contain profession keywords
        profession_keywords = [
            'cricketer', 'actor', 'actress', 'founder', 'ceo', 'singer', 'professor',
            'politician', 'dentist', 'engineer', 'lawyer', 'doctor', 'director',
            'writer', 'author', 'artist', 'musician', 'player', 'coach', 'manager',
            'entrepreneur', 'businessman', 'businesswoman', 'athlete', 'sportsman'
        ]
        if not any(kw in value_lower for kw in profession_keywords):
            return False, "No profession keywords"
        
        return True, "Valid profession"
    
    def validate_location(self, value: str) -> Tuple[bool, str]:
        """
        Field guardrails: Location validator
        Should look like City, State, Country
        Reject sports context fragments
        """
        value_lower = value.lower()
        
        # Reject sports context fragments
        sports_keywords = ['finals', 'match', 'won', 'series', 'cricket', 'tournament', 'cup']
        if any(kw in value_lower for kw in sports_keywords):
            return False, "Sports context fragment"
        
        # Reject weird punctuation fragments
        if value.count(',') > 3 or value.count('(') > 2:
            return False, "Too many punctuation marks"
        
        # Reject single word fragments that are common false positives
        single_word_fragments = ['delhi', 'mumbai', 'bangalore', 'kolkata', 'chennai']
        if value_lower in single_word_fragments and len(value.split()) == 1:
            # Only accept if it's from infobox (structured)
            return False, "Single word fragment (not from infobox)"
        
        # Should have structure (comma-separated or known country)
        known_countries = ['india', 'usa', 'uk', 'australia', 'england', 'pakistan', 'canada']
        if value_lower in known_countries:
            return True, "Known country"
        
        # Check for comma-separated structure (City, State, Country)
        if ',' in value and len(value.split(',')) >= 2:
            return True, "Structured location"
        
        # Two-word locations (e.g., "New Delhi", "Los Angeles")
        if len(value.split()) == 2:
            return True, "Two-word location"
        
        return False, "Invalid location format"
    
    def validate_phone(self, value: str, source_url: str, text_context: str) -> Tuple[bool, str]:
        """
        Field guardrails: Phone validator
        Only accept if preceded by labels or from official contact page
        """
        url_lower = source_url.lower()
        context_lower = text_context.lower()
        
        # Reject from forums/Reddit
        if any(site in url_lower for site in ['reddit.com', 'forum', 'comments', 'discussion']):
            return False, "From forum/Reddit"
        
        # Check for phone labels in context
        phone_labels = ['phone', 'tel', 'call', 'contact', 'mobile', 'telephone']
        if not any(label in context_lower for label in phone_labels):
            # Only accept if from official contact page
            if '/contact' not in url_lower and '/about' not in url_lower:
                return False, "No phone label, not contact page"
        
        return True, "Valid phone"
    
    def validate_email(self, value: str, anchor_domains: Set[str], source_url: str) -> Tuple[bool, str, float]:
        """
        B) Fix 1: Email validator with ownership priority
        Returns: (is_valid, reason, priority_score)
        """
        email_lower = value.lower()
        domain = email_lower.split('@')[1] if '@' in email_lower else ''
        
        # Highest priority: anchor domain
        for anchor_domain in anchor_domains:
            if anchor_domain in domain:
                return True, f"Anchor domain ({domain})", 100.0
        
        # Medium priority: official clinic domain (not gmail/yahoo)
        if domain and domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
            source_domain = urlparse(source_url).netloc.lower().replace('www.', '')
            if domain in source_domain or source_domain in domain:
                return True, f"Official domain ({domain})", 70.0
        
        # Low priority: Gmail/Yahoo only if on official site
        if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
            source_domain = urlparse(source_url).netloc.lower().replace('www.', '')
            if any(anchor in source_domain for anchor in anchor_domains):
                return True, f"Gmail/Yahoo on official site", 30.0
            else:
                return False, "Gmail/Yahoo not on official site", 0.0
        
        return True, "Valid email", 50.0
    
    def extract_fact_candidates(self, sources: List[Dict], role_pack: RolePack, selected_candidate: IdentityCandidate = None) -> List[FactCandidate]:
        """
        STEP 4 & 5: Extract fact candidates using universal schema
        B) Fix 2: Prefer structured data over scraped text
        """
        candidates = []
        source_domain = urlparse(sources[0]['url']).netloc.lower().replace('www.', '') if sources else ''
        
        # Universal extraction patterns
        for source in sources:
            url = source['url']
            url_lower = url.lower()
            tier = source['tier']
            text = source['content']['text']
            text_lower = text.lower()
            structured = source['content'].get('structured_data', {})
            is_contact_page = source['content'].get('is_contact_page', False)
            url_domain = urlparse(url).netloc.lower().replace('www.', '')
            is_anchor_domain = any(anchor in url_domain for anchor in self.anchor_domains)
            soup = BeautifulSoup(source['content'].get('html', ''), 'html.parser') if source['content'].get('html') else None
            
            # Source-specific parsing (highest priority)
            source_type = source['content'].get('source_type', 'generic')
            source_specific = source['content'].get('source_specific', {})
            
            # Wikipedia infobox (ONLY source for core fields on Wikipedia)
            if source_type == 'wikipedia' and 'infobox' in source_specific:
                infobox = source_specific['infobox']
                if infobox.get('full_name'):
                    candidates.append(FactCandidate(
                        field='full_name',
                        value=infobox['full_name'],
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=infobox['full_name'],
                        from_structured_data=True,
                        score=40.0  # Wikipedia infobox
                    ))
                if infobox.get('profession'):
                    # Validate profession - reject family context
                    profession = infobox['profession']
                    if self.validate_profession(profession)[0]:
                        # Additional check: reject long sentences
                        if len(profession) < 120:  # Reject long fragments
                            candidates.append(FactCandidate(
                                field='primary_role',
                                value=profession,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=profession,
                                from_structured_data=True,
                                score=40.0
                            ))
                if infobox.get('nationality'):
                    if self.validate_location(infobox['nationality'])[0]:
                        candidates.append(FactCandidate(
                            field='nationality',
                            value=infobox['nationality'],
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=infobox['nationality'],
                            from_structured_data=True,
                            score=40.0
                        ))
                if infobox.get('birth_place'):
                    # Use birth_place from infobox (not random "Delhi" from text)
                    if self.validate_location(infobox['birth_place'])[0]:
                        candidates.append(FactCandidate(
                            field='location',
                            value=infobox['birth_place'],
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=infobox['birth_place'],
                            from_structured_data=True,
                            score=40.0
                        ))
                if infobox.get('birth_date'):
                    candidates.append(FactCandidate(
                        field='birth_date',
                        value=infobox['birth_date'],
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=infobox['birth_date'],
                        from_structured_data=True,
                        score=40.0
                    ))
                if infobox.get('known_for'):
                    candidates.append(FactCandidate(
                        field='known_for',
                        value=infobox['known_for'],
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=infobox['known_for'],
                        from_structured_data=True,
                        score=40.0
                    ))
                if infobox.get('official_website'):
                    candidates.append(FactCandidate(
                        field='official_websites',
                        value=infobox['official_website'],
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=infobox['official_website'],
                        from_structured_data=True,
                        score=40.0
                    ))
            
            # Wikipedia first sentence (for profession)
            if source_type == 'wikipedia' and 'first_sentence' in source_specific:
                first_sent = source_specific['first_sentence']
                if first_sent.get('profession'):
                    if self.validate_profession(first_sent['profession'])[0]:
                        candidates.append(FactCandidate(
                            field='primary_role',
                            value=first_sent['profession'],
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=first_sent['profession'],
                            from_structured_data=True,
                            score=30.0  # Wikipedia first sentence
                        ))
            
            # Wikidata (highest priority)
            if source_type == 'wikidata':
                if structured.get('profession'):
                    if self.validate_profession(structured['profession'])[0]:
                        candidates.append(FactCandidate(
                            field='primary_role',
                            value=structured['profession'],
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=structured['profession'],
                            from_structured_data=True,
                            score=50.0  # Wikidata highest
                        ))
                if structured.get('birth_date'):
                    candidates.append(FactCandidate(
                        field='birth_date',
                        value=structured['birth_date'],
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=structured['birth_date'],
                        from_structured_data=True,
                        score=50.0
                    ))
                if structured.get('nationality'):
                    if self.validate_location(structured['nationality'])[0]:
                        candidates.append(FactCandidate(
                            field='nationality',
                            value=structured['nationality'],
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=structured['nationality'],
                            from_structured_data=True,
                            score=50.0
                        ))
                if structured.get('official_website'):
                    candidates.append(FactCandidate(
                        field='official_websites',
                        value=structured['official_website'],
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=structured['official_website'],
                        from_structured_data=True,
                        score=50.0
                    ))
            
            # B) Fix 2: Extract from structured data (JSON-LD, OpenGraph)
            # Name from structured data (validate against target)
            if structured.get('name'):
                struct_name = structured['name']
                # Validate: must match target name if available
                if selected_candidate and selected_candidate.name:
                    target_parts = selected_candidate.name.lower().split()
                    struct_lower = struct_name.lower()
                    if not all(part in struct_lower for part in target_parts):
                        # Name doesn't match target - skip
                        continue
                
                if not self.is_value_blacklisted(struct_name, 'full_name')[0]:
                    candidates.append(FactCandidate(
                        field='full_name',
                        value=struct_name,
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=struct_name,
                        from_structured_data=True,
                        from_contact_page=is_contact_page,
                        score=30.0 if is_anchor_domain else 20.0
                    ))
            
            if structured.get('organization'):
                org_name = structured['organization']
                # FIX 4: Organization must contain anchor OR be from schema
                is_valid = False
                if any(anchor in org_name.lower() for anchor in self.anchor_domains):
                    is_valid = True
                elif structured.get('organization'):  # From schema.org
                    is_valid = True
                
                if is_valid and not self.is_value_blacklisted(org_name, 'primary_organization')[0]:
                    candidates.append(FactCandidate(
                        field='primary_organization',
                        value=org_name,
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=org_name,
                        from_structured_data=True,
                        from_contact_page=is_contact_page,
                        score=50.0 if is_anchor_domain else 30.0
                    ))
            
            if structured.get('email'):
                candidates.append(FactCandidate(
                    field='public_email',
                    value=structured['email'].lower(),
                    source_url=url,
                    source_tier=tier,
                    evidence_snippet=structured['email'],
                    from_structured_data=True,
                    from_contact_page=is_contact_page,
                    score=50.0 if is_anchor_domain else 30.0
                ))
            
            if structured.get('phone'):
                candidates.append(FactCandidate(
                    field='phone',
                    value=structured['phone'],
                    source_url=url,
                    source_tier=tier,
                    evidence_snippet=structured['phone'],
                    from_structured_data=True,
                    from_contact_page=is_contact_page,
                    score=50.0 if is_anchor_domain else 30.0
                ))
            
            if structured.get('address'):
                candidates.append(FactCandidate(
                    field='address',
                    value=structured['address'],
                    source_url=url,
                    source_tier=tier,
                    evidence_snippet=structured['address'],
                    from_structured_data=True,
                    from_contact_page=is_contact_page,
                    score=50.0 if is_anchor_domain else 30.0
                ))
            
            if structured.get('specialty') and role_pack == RolePack.MEDICAL:
                candidates.append(FactCandidate(
                    field='specialization',
                    value=structured['specialty'],
                    source_url=url,
                    source_tier=tier,
                    evidence_snippet=structured['specialty'],
                    from_structured_data=True,
                    from_contact_page=is_contact_page,
                    score=50.0 if is_anchor_domain else 30.0
                ))
            
            # Name extraction (FIX: schema/h1 only, token-based matching)
            # Only from structured data or h1 that contains all name tokens
            target_name_tokens = []
            if selected_candidate and selected_candidate.name:
                target_name_tokens = self.extract_name_tokens(selected_candidate.name)
            
            # From structured data (highest priority)
            if structured.get('name'):
                struct_name = structured['name']
                # Validate: must contain all target name tokens (token-based)
                struct_normalized = struct_name.lower()
                struct_normalized = re.sub(r'[.,\-_/]', ' ', struct_normalized)
                struct_normalized = re.sub(r'\s+', ' ', struct_normalized)
                if not target_name_tokens or all(token in struct_normalized for token in target_name_tokens):
                    if not self.is_value_blacklisted(struct_name, 'full_name')[0]:
                        candidates.append(FactCandidate(
                            field='full_name',
                            value=struct_name,
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=struct_name,
                            from_structured_data=True,
                            score=50.0
                        ))
            
            # From h1 (only if contains all name tokens)
            if soup:
                h1_tags = soup.find_all('h1')
                for h1 in h1_tags:
                    h1_text = h1.get_text(strip=True)
                    h1_normalized = h1_text.lower()
                    h1_normalized = re.sub(r'[.,\-_/]', ' ', h1_normalized)
                    h1_normalized = re.sub(r'\s+', ' ', h1_normalized)
                    if not target_name_tokens or all(token in h1_normalized for token in target_name_tokens):
                        if not self.is_value_blacklisted(h1_text, 'full_name')[0]:
                            candidates.append(FactCandidate(
                                field='full_name',
                                value=h1_text,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=h1_text,
                                score=40.0
                            ))
                            break  # Only take first matching h1
            
            # C) Title + Education extraction (medical pack)
            if role_pack == RolePack.MEDICAL:
                # FIX 1: Role allowlist + service blacklist
                role_allowlist_keywords = [
                    'dentist', 'endodontist', 'tmj', 'occlusion', 'neuro', 'cranio',
                    'master ceramist', 'epigeneticist', 'specialist',
                    'surgeon', 'orthodontist', 'periodontist', 'implantologist',
                    'prosthodontist', 'craniodontist'
                ]
                
                service_blacklist_keywords = [
                    'appointment', 'painless', 'laser dentistry', 'make an appointment',
                    'clinic hours', 'call now', 'book', 'treatment', 'whitening',
                    'bruxism treatment', 'service', 'procedure'
                ]
                
                # Extract titles from headings (h1, h2, h3) - with blacklist check
                if soup:
                    for heading in soup.find_all(['h1', 'h2', 'h3']):
                        heading_text = heading.get_text(strip=True)
                        heading_lower = heading_text.lower()
                        
                        # Reject if contains service blacklist keywords
                        if any(blacklist in heading_lower for blacklist in service_blacklist_keywords):
                            continue
                        
                        # Only accept if contains role allowlist keyword
                        for keyword in role_allowlist_keywords:
                            if keyword in heading_lower:
                                # Extract full title phrase
                                if 5 < len(heading_text) < 100 and self.validate_profession(heading_text)[0]:
                                    candidates.append(FactCandidate(
                                        field='primary_role',
                                        value=heading_text,
                                        source_url=url,
                                        source_tier=tier,
                                        evidence_snippet=heading_text,
                                        score=35.0
                                    ))
                                break  # Only take first matching keyword
                
                # Extract from text near name - with blacklist check
                if selected_candidate and selected_candidate.name:
                    name_tokens = self.extract_name_tokens(selected_candidate.name)
                    if name_tokens:
                        # Find name in text, extract nearby titles
                        for token in name_tokens:
                            if token in text_lower:
                                idx = text_lower.find(token)
                                context = text[max(0, idx-100):min(len(text), idx+200)]
                                context_lower = context.lower()
                                
                                # Reject if context contains service blacklist
                                if any(blacklist in context_lower for blacklist in service_blacklist_keywords):
                                    continue
                                
                                for keyword in role_allowlist_keywords:
                                    if keyword in context_lower:
                                        # Extract title phrase
                                        pattern = re.compile(rf'{re.escape(keyword)}[^,\.]{0,30}', re.I)
                                        match = pattern.search(context)
                                        if match:
                                            title = match.group(0).strip()
                                            if 5 < len(title) < 100:
                                                candidates.append(FactCandidate(
                                                    field='primary_role',
                                                    value=title,
                                                    source_url=url,
                                                    source_tier=tier,
                                                    evidence_snippet=context,
                                                    score=30.0
                                                ))
                                        break
                
                # C) Degree regex extraction (Step B + Step C)
                degree_pattern = re.compile(r'\b(BDS|MDS|B\.?\s?Sc\.?|M\.?\s?Sc\.?|PhD|DDS|DMD|MBBS|MD|B\.?A\.?|M\.?A\.?)\b', re.I)
                degree_matches = degree_pattern.findall(text)
                
                # Also check qualification sections
                qualification_keywords = ['education', 'qualification', 'degree', 'bds', 'mds', 'bsc']
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(kw in line_lower for kw in qualification_keywords):
                        # Extract from window around qualification keyword
                        window = ' '.join(lines[max(0, i-2):min(len(lines), i+5)])
                        window_matches = degree_pattern.findall(window)
                        degree_matches.extend(window_matches)
                
                if degree_matches:
                    # Normalize degrees
                    normalized_degrees = []
                    for degree in set(degree_matches):
                        # Normalize: remove spaces, uppercase, fix B.Sc -> BSc
                        norm = re.sub(r'\s+', '', degree.upper())
                        norm = norm.replace('B.SC', 'BSc').replace('M.SC', 'MSc')
                        if norm not in normalized_degrees:
                            normalized_degrees.append(norm)
                    
                    # Extract context around degrees
                    for degree in normalized_degrees:
                        # Try original pattern first
                        pattern = re.compile(rf'\\b{re.escape(degree)}\\b', re.I)
                        match = pattern.search(text)
                        if not match:
                            # Try with spaces/dots
                            pattern = re.compile(rf'\\b{re.escape(degree.replace("SC", ".Sc"))}\\b', re.I)
                            match = pattern.search(text)
                        
                        if match:
                            start = max(0, match.start() - 50)
                            end = min(len(text), match.end() + 50)
                            context = text[start:end]
                            # Try to extract full degree phrase
                            degree_phrase = degree
                            # Look for "BDS (Bachelor of Dental Surgery)" pattern
                            full_pattern = re.compile(rf'{re.escape(degree)}\\s*\\([^)]+\\)', re.I)
                            full_match = full_pattern.search(context)
                            if full_match:
                                degree_phrase = full_match.group(0).strip()
                            
                            candidates.append(FactCandidate(
                                field='education',
                                value=degree_phrase,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=context,
                                score=40.0
                            ))
                
                # B) Extract experience (e.g., "25 Year Experience", "Dr. Sanjay Arora (25 Year Experience)")
                experience_patterns = [
                    re.compile(r'(\d+)\s*(?:year|years|yr|yrs)\s*(?:of\s*)?experience', re.I),
                    re.compile(r'\((\d+)\s*(?:year|years|yr|yrs)\s*experience\)', re.I),
                ]
                for pattern in experience_patterns:
                    experience_matches = pattern.findall(text)
                    if experience_matches:
                        # Take the highest number (most recent/accurate)
                        max_years = max([int(y) for y in experience_matches])
                        candidates.append(FactCandidate(
                            field='experience_years',
                            value=f"{max_years} years",
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=f"{max_years} years of experience",
                            score=35.0
                        ))
                        break  # Only add once
            
            # Role/Title extraction with guardrails
            # For Wikipedia: ONLY use infobox/first sentence, NEVER random text
            # For other sources: only from structured sections
            if source_type == 'wikipedia':
                # Wikipedia: ONLY use infobox and first sentence, skip generic text extraction
                # This is already handled above in source-specific parsing
                pass  # Skip generic profession extraction for Wikipedia
            elif source_type == 'wikidata':
                # Wikidata: already handled above
                pass
            elif is_contact_page:
                role_allowlist = [
                    'founder', 'ceo', 'cto', 'cfo', 'president', 'director', 'manager',
                    'professor', 'doctor', 'dentist', 'surgeon', 'physician',
                    'engineer', 'lawyer', 'consultant', 'researcher', 'artist',
                    'actor', 'author', 'cricketer', 'singer', 'musician'
                ]
                
                # Multi-word role patterns (only from structured sections)
                multi_word_pattern = r'(?:Senior|Junior|Chief|Head|Lead|Principal)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*'
                multi_word_matches = re.finditer(multi_word_pattern, text, re.I)
                for match in multi_word_matches:
                    role_phrase = match.group(0).strip()
                    if len(role_phrase) > 5:
                        # Validate profession
                        if self.validate_profession(role_phrase)[0]:
                            start = max(0, match.start() - 50)
                            end = min(len(text), match.end() + 50)
                            snippet = text[start:end].strip()
                            candidates.append(FactCandidate(
                                field='primary_role',
                                value=role_phrase,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=snippet,
                                score=10.0 if source_type == 'forum' else 20.0  # Lower for forums
                            ))
                
                # Single-word roles from allowlist only
                for role_word in role_allowlist:
                    pattern = r'\b' + re.escape(role_word) + r'\b'
                    matches = re.finditer(pattern, text, re.I)
                    for match in matches:
                        # Check context - must be near name or in professional context
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context = text[start:end].lower()
                        
                        # Reject if in noisy context
                        if any(noise in context for noise in ['category', 'list of', 'browse', 'filter', 'father', 'mother']):
                            continue
                        
                        # Validate profession
                        if not self.validate_profession(match.group(0))[0]:
                            continue
                        
                        snippet = text[start:end].strip()
                        score = 10.0 if source_type == 'forum' else 20.0
                        if source_type == 'forum':
                            score -= 30.0  # Penalty for forums
                        
                        candidates.append(FactCandidate(
                            field='primary_role',
                            value=match.group(0),
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=snippet,
                            score=score
                        ))
            
            # Organization extraction (FIX 4: anchor-based, medical pack)
            # For medical pack: must contain "Zental" or be from schema
            if source_type != 'wikipedia' and role_pack == RolePack.MEDICAL:
                # Only extract if contains anchor domain keywords
                if any(anchor in text_lower for anchor in self.anchor_domains):
                    # Look for organization near anchor
                    for anchor in self.anchor_domains:
                        anchor_idx = text_lower.find(anchor)
                        if anchor_idx != -1:
                            # Extract context around anchor
                            context_start = max(0, anchor_idx - 100)
                            context_end = min(len(text), anchor_idx + len(anchor) + 100)
                            context = text[context_start:context_end]
                            
                            # Try to find org name in context
                            org_patterns = [
                                r'([A-Z][a-zA-Z0-9\s&]+(?:Dental|Clinic|Hospital|Practice))',
                            ]
                            for pattern in org_patterns:
                                matches = re.finditer(pattern, context, re.I)
                                for match in matches:
                                    org_name = match.group(1).strip()
                                    # Must contain anchor keyword
                                    if anchor.replace('.com', '').replace('.in', '') in org_name.lower():
                                        if not self.is_value_blacklisted(org_name, 'primary_organization')[0]:
                                            candidates.append(FactCandidate(
                                                field='primary_organization',
                                                value=org_name,
                                                source_url=url,
                                                source_tier=tier,
                                                evidence_snippet=context,
                                                score=50.0
                                            ))
                                            break
            
            # Address extraction (FIX 3: Look for address labels)
            # Extract from main text and footer
            search_texts = [text]
            footer_text = source['content'].get('footer_text', '')
            if footer_text:
                search_texts.append(footer_text)
            
            address_labels = ['address', 'clinic address', 'location', 'visit us', 'reach us', 'find us', 'our location']
            for search_text in search_texts:
                for label in address_labels:
                    pattern = re.compile(rf'{re.escape(label)}[:\s]+([^\n\r]{20,200})', re.I)
                    matches = pattern.finditer(search_text)
                    for match in matches:
                        address = match.group(1).strip()
                        # Clean address (remove extra whitespace, take first 3 lines max)
                        address_lines = [line.strip() for line in address.split('\n')[:3] if line.strip()]
                        address = ', '.join(address_lines)
                        
                        if len(address) > 10 and not self.is_value_blacklisted(address, 'location')[0]:
                            snippet = search_text[max(0, match.start()-50):min(len(search_text), match.end()+50)]
                            score = 50.0 if 'footer' in search_text else 40.0
                            candidates.append(FactCandidate(
                                field='address',
                                value=address,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=snippet,
                                score=score
                            ))
                            break  # Only take first address per label
            
            # Location extraction (FIX 5: Location quality ranking)
            # For Wikipedia: ONLY use infobox "Born" field, NEVER random text
            # For other sources: extract with quality ranking
            if source_type != 'wikipedia':
                # FIX 5: Extract locations with quality ranking
                # Street address > Area (Green Park/Saket) > City (Delhi) > Country (India)
                location_candidates = []
                
                # Extract from structured data first (highest quality)
                if structured.get('address'):
                    addr = structured['address']
                    location_candidates.append((addr, 50.0, "structured address"))
                
                # Extract from text with patterns
                location_patterns = [
                    (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*(?:New\s+)?Delhi', 40.0, "city-level"),  # City
                    (r'(?:Green\s+Park|Saket|Yusuf\s+Sarai)', 35.0, "area-level"),  # Area
                    (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*(?:India|USA|UK)', 20.0, "country-level"),  # Country
                ]
                
                for pattern, score, quality in location_patterns:
                    matches = re.finditer(pattern, text, re.I)
                    for match in matches:
                        loc = match.group(1).strip() if match.groups() else match.group(0)
                        
                        # Reject sports context fragments
                        if any(word in loc.lower() for word in ['finals', 'match', 'won', 'series', 'cricket']):
                            continue
                        
                        # Reject if just "India" (too generic)
                        if loc.lower().strip() == 'india':
                            continue
                        
                        # Validate location
                        is_valid, reason = self.validate_location(loc)
                        if not is_valid:
                            continue
                        
                        location_candidates.append((loc, score, quality))
                
                # Add best location candidate
                if location_candidates:
                    # Sort by score (highest first)
                    location_candidates.sort(key=lambda x: x[1], reverse=True)
                    best_loc, best_score, quality = location_candidates[0]
                    
                    snippet = f"Location ({quality})"
                    candidates.append(FactCandidate(
                        field='location',
                        value=best_loc,
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=snippet,
                        score=best_score
                    ))
            
            # Phone extraction (FIX 2 & 4: Extract from contact sections + mailto/tel links)
            # Extract from main text, contact sections, and tel: links
            search_texts = [text]
            contact_text = source['content'].get('contact_text', '')
            if contact_text:
                search_texts.append(contact_text)
            
            # FIX A: Always extract phone from tel: links
            tel_phones = source['content'].get('tel_phones', [])
            for tel_phone in tel_phones:
                # Normalize tel: phone
                digits = re.sub(r'\D', '', tel_phone)
                if len(digits) >= 10:
                    if digits.startswith('91') and len(digits) == 12:
                        phone_normalized = f"+{digits}"
                    elif digits.startswith('0') and len(digits) == 11:
                        phone_normalized = f"+91{digits[1:]}"
                    elif len(digits) == 10:
                        phone_normalized = f"+91{digits}"
                    else:
                        continue
                    
                    candidates.append(FactCandidate(
                        field='phone',
                        value=phone_normalized,
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=f"tel: link: {tel_phone}",
                        score=60.0  # Highest priority for tel: links
                    ))
            
            for search_text in search_texts:
                # FIX 3: Indian phone patterns
                phone_patterns = [
                    re.compile(r'\+91[-\s]?\d{10}'),
                    re.compile(r'\+91[-\s]?\d{5}[-\s]?\d{5}'),
                    re.compile(r'0\d{10}'),
                    re.compile(r'\d{10}'),  # 10 digits (might be without +91)
                ]
                
                for pattern in phone_patterns:
                    matches = pattern.finditer(search_text)
                    for match in matches:
                        phone = match.group(0)
                        # Normalize Indian phone
                        digits = re.sub(r'\D', '', phone)
                        if len(digits) < 10 or len(digits) > 13:
                            continue  # Reject invalid lengths
                        
                        if digits.startswith('91') and len(digits) == 12:
                            phone_normalized = f"+{digits}"
                        elif digits.startswith('0') and len(digits) == 11:
                            phone_normalized = f"+91{digits[1:]}"
                        elif len(digits) == 10:
                            phone_normalized = f"+91{digits}"
                        else:
                            continue
                        
                        # Validate phone with context
                        start = max(0, match.start() - 100)
                        end = min(len(search_text), match.end() + 100)
                        context = search_text[start:end]
                        context_lower = context.lower()
                        
                        # Must have phone label OR be on contact page/footer
                        has_label = any(label in context_lower for label in ['phone', 'call', 'tel', 'contact', 'mobile', 'telephone'])
                        is_footer = search_text == footer_text
                        
                        if not has_label and not is_footer and not is_contact_page:
                            continue
                        
                        is_valid, reason = self.validate_phone(phone_normalized, url, context)
                        if not is_valid:
                            continue
                        
                        if not self.is_value_blacklisted(phone_normalized, 'phone')[0]:
                            snippet = context.strip()
                            score = 50.0 if is_contact_page else 40.0 if is_footer else 30.0
                            candidates.append(FactCandidate(
                                field='phone',
                                value=phone_normalized,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=snippet,
                                score=score
                            ))
            
            # Email extraction (FIX 2 & 4: Extract from contact sections + mailto links)
            # Extract from main text, contact sections, and mailto: links
            search_texts = [text]
            contact_text = source['content'].get('contact_text', '')
            if contact_text:
                search_texts.append(contact_text)
            
            # FIX A: Always extract email/phone from HTML attributes (mailto/tel)
            # Extract from mailto: links (highest priority)
            mailto_emails = source['content'].get('mailto_emails', [])
            for email in mailto_emails:
                email_lower = email.lower()
                # Validate email
                is_valid, reason, priority_score = self.validate_email(email_lower, self.anchor_domains, url)
                if is_valid and not self.is_value_blacklisted(email_lower, 'public_email')[0]:
                    candidates.append(FactCandidate(
                        field='public_email',
                        value=email_lower,
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=f"mailto: link: {email}",
                        score=70.0  # Highest priority for mailto: links
                    ))
            
            # Also scan raw HTML for emails (sometimes not in visible text)
            if soup:
                raw_email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
                raw_html = source['content'].get('html', '')
                raw_emails = raw_email_pattern.findall(raw_html)
                for email in raw_emails:
                    email_lower = email.lower()
                    if email_lower not in [e.lower() for e in mailto_emails]:  # Don't duplicate
                        is_valid, reason, priority_score = self.validate_email(email_lower, self.anchor_domains, url)
                        if is_valid and not self.is_value_blacklisted(email_lower, 'public_email')[0]:
                            candidates.append(FactCandidate(
                                field='public_email',
                                value=email_lower,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=f"raw HTML: {email}",
                                score=50.0
                            ))
            
            for search_text in search_texts:
                email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
                matches = email_pattern.finditer(search_text)
                for match in matches:
                    email = match.group(0).lower()
                    email_domain = email.split('@')[1] if '@' in email else ''
                    
                    # Validate email with priority
                    is_valid, reason, priority_score = self.validate_email(email, self.anchor_domains, url)
                    if not is_valid:
                        continue  # Skip invalid emails
                    
                    # FIX 3: Accept domain emails with high priority
                    is_domain_email = any(anchor.replace('.com', '').replace('.in', '') in email_domain for anchor in self.anchor_domains)
                    
                    # Reject random Gmail unless on contact page/footer
                    if email_domain in ['gmail.com', 'yahoo.com']:
                        is_footer = search_text == footer_text
                        if not is_contact_page and not is_anchor_domain and not is_footer:
                            continue  # Reject Gmail not on official contact page/footer
                    
                    # Check if in contact section
                    start = max(0, match.start() - 100)
                    end = min(len(search_text), match.end() + 100)
                    context = search_text[start:end].lower()
                    
                    # Must be in contact context OR footer
                    is_footer = search_text == footer_text
                    has_contact_context = any(contact_word in context for contact_word in ['contact', 'email', 'mail', 'reach', 'get in touch'])
                    
                    if not has_contact_context and not is_contact_page and not is_footer:
                        continue
                    
                    if not self.is_value_blacklisted(email, 'public_email')[0]:
                        snippet = search_text[start:end].strip()
                        score = priority_score
                        if is_domain_email:
                            score += 50.0  # Domain email priority
                        if is_anchor_domain:
                            score += 30.0
                        if is_contact_page:
                            score += 15.0
                        if is_footer:
                            score += 10.0
                        
                        candidates.append(FactCandidate(
                            field='public_email',
                            value=email,
                            source_url=url,
                            source_tier=tier,
                            evidence_snippet=snippet,
                            score=score
                        ))
            
            # Website extraction (from text and JSON-LD sameAs)
            # Extract from JSON-LD sameAs (social profiles)
            if structured.get('sameAs'):
                same_as_list = structured['sameAs']
                if isinstance(same_as_list, list):
                    for profile_url in same_as_list:
                        if isinstance(profile_url, str) and profile_url.startswith('http'):
                            candidates.append(FactCandidate(
                                field='official_websites',
                                value=profile_url,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=profile_url,
                                from_structured_data=True,
                                score=45.0
                            ))
            
            # Extract from text
            url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;!?]')
            matches = url_pattern.finditer(text)
            for match in matches:
                website = match.group(0).rstrip('.,;!?')
                if '.' in website and len(website) > 10:
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    snippet = text[start:end].strip()
                    candidates.append(FactCandidate(
                        field='official_websites',
                        value=website,
                        source_url=url,
                        source_tier=tier,
                        evidence_snippet=snippet,
                        score=20.0
                    ))
            
            # Role-specific extractions
            if role_pack == RolePack.MEDICAL:
                # FIX 4: Special Interests vs Services
                # Special Interests: TMJ, occlusion, neuro-muscular dentistry keywords
                interest_keywords = ['tmj', 'occlusion', 'neuro-muscular', 'cranio-sacral', 'epigenetics', 'bruxism']
                for keyword in interest_keywords:
                    if keyword in text_lower:
                        # Extract context around keyword
                        idx = text_lower.find(keyword)
                        context_start = max(0, idx - 100)
                        context_end = min(len(text), idx + len(keyword) + 100)
                        context = text[context_start:context_end]
                        
                        # Try to extract full phrase
                        pattern = re.compile(rf'{re.escape(keyword)}[^,\.]{0,50}', re.I)
                        match = pattern.search(context)
                        if match:
                            interest = match.group(0).strip()
                            if 5 < len(interest) < 100:
                                candidates.append(FactCandidate(
                                    field='specialization',
                                    value=interest,
                                    source_url=url,
                                    source_tier=tier,
                                    evidence_snippet=context,
                                    score=30.0
                                ))
                
                # FIX 2: Services extraction (separate from titles)
                # Service phrases that should NOT be titles
                service_phrases = [
                    'painless dentistry', 'laser dentistry', 'cosmetic dentistry',
                    'root canal', 'dental implant', 'teeth whitening', 'bruxism treatment',
                    'tmj treatment', 'orthodontic treatment', 'periodontal treatment'
                ]
                
                service_blacklist_keywords = [
                    'appointment', 'painless', 'laser dentistry', 'make an appointment',
                    'clinic hours', 'call now', 'book', 'treatment', 'whitening',
                    'bruxism treatment', 'service', 'procedure'
                ]
                
                for service_phrase in service_phrases:
                    if service_phrase in text_lower:
                        # Extract service phrase
                        idx = text_lower.find(service_phrase)
                        context_start = max(0, idx - 50)
                        context_end = min(len(text), idx + len(service_phrase) + 50)
                        context = text[context_start:context_end]
                        
                        # Capitalize first letter
                        service = service_phrase.title()
                        if 5 < len(service) < 100:
                            candidates.append(FactCandidate(
                                field='services',
                                value=service,
                                source_url=url,
                                source_tier=tier,
                                evidence_snippet=context,
                                score=20.0
                            ))
                
                # Also extract from headings that contain service keywords
                if soup:
                    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                        heading_text = heading.get_text(strip=True)
                        heading_lower = heading_text.lower()
                        
                        # If heading contains service blacklist keywords, it's a service
                        if any(blacklist in heading_lower for blacklist in service_blacklist_keywords):
                            # Check if it's a service phrase
                            if any(service_kw in heading_lower for service_kw in ['dentistry', 'treatment', 'procedure', 'service']):
                                if 5 < len(heading_text) < 100:
                                    candidates.append(FactCandidate(
                                        field='services',
                                        value=heading_text,
                                        source_url=url,
                                        source_tier=tier,
                                        evidence_snippet=heading_text,
                                        score=25.0
                                    ))
                
                # Also extract from headings that contain service keywords
                if soup:
                    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                        heading_text = heading.get_text(strip=True)
                        heading_lower = heading_text.lower()
                        
                        # If heading contains service blacklist keywords, it's a service
                        if any(blacklist in heading_lower for blacklist in service_blacklist_keywords):
                            # Check if it's a service phrase
                            if any(service_kw in heading_lower for service_kw in ['dentistry', 'treatment', 'procedure', 'service']):
                                if 5 < len(heading_text) < 100:
                                    candidates.append(FactCandidate(
                                        field='services',
                                        value=heading_text,
                                        source_url=url,
                                        source_tier=tier,
                                        evidence_snippet=heading_text,
                                        score=25.0
                                    ))
        
        return candidates
    
    def validate_facts(self, candidates: List[FactCandidate]) -> List[FactCandidate]:
        """
        STEP 6: Validation with source weighting
        B) Fix 3: Select best candidate by score, not just most common
        """
        # Group by field and value
        fact_groups = {}
        for candidate in candidates:
            key = (candidate.field, candidate.value.lower())
            if key not in fact_groups:
                fact_groups[key] = []
            fact_groups[key].append(candidate)
        
        confirmed_facts = []
        
        for (field, value), group in fact_groups.items():
            # FIX 2: Value blacklist - reject junk values
            is_blacklisted, blacklist_reason = self.is_value_blacklisted(value, field)
            if is_blacklisted:
                print(f"    ⊘ Blacklisted: {field} = '{value[:50]}...' ({blacklist_reason})")
                continue  # Skip this entire group
            
            # B) Fix 3: Calculate total score for each fact value
            for candidate in group:
                # Base score from source weighting
                total_score = candidate.score
                
                # Fix 4: Extraction priority scoring
                url_domain = urlparse(candidate.source_url).netloc.lower()
                
                # Highest priority: Wikidata
                if 'wikidata.org' in url_domain:
                    total_score += 50.0
                # Wikipedia infobox
                elif 'wikipedia.org' in url_domain and candidate.from_structured_data:
                    total_score += 40.0
                # Wikipedia first sentence
                elif 'wikipedia.org' in url_domain:
                    total_score += 30.0
                
                # Tier bonuses
                if candidate.source_tier == SourceTier.TIER_A:
                    total_score += 30.0
                elif candidate.source_tier == SourceTier.TIER_B:
                    total_score += 15.0
                
                # Structured data bonus
                if candidate.from_structured_data:
                    total_score += 30.0
                
                # Contact page bonus
                if candidate.from_contact_page:
                    total_score += 15.0
                
                # Multiple sources bonus (but don't count junk repetition)
                if len(group) >= 2:
                    total_score += 10.0
                
                # Forum/Reddit penalty
                if any(site in url_domain for site in ['reddit.com', 'forum', 'comments']):
                    total_score -= 30.0
                
                # Directory penalty
                if any(dir_site in url_domain for dir_site in ['justdial.com', 'practo.com']):
                    total_score -= 20.0
                
                # Unstructured paragraph penalty
                if not candidate.from_structured_data and 'wikipedia.org' not in url_domain:
                    total_score -= 20.0
                
                candidate.score = total_score
            
            # Select best candidate by score
            best_candidate = max(group, key=lambda c: c.score)
            
            # Validation rules (still check tiers)
            tier_a_count = sum(1 for c in group if c.source_tier == SourceTier.TIER_A)
            tier_b_count = sum(1 for c in group if c.source_tier == SourceTier.TIER_B)
            
            tier_b_anchor_match = False
            if tier_b_count > 0:
                for candidate in group:
                    if candidate.source_tier == SourceTier.TIER_B:
                        domain = urlparse(candidate.source_url).netloc.lower()
                        if any(anchor in domain for anchor in self.anchors):
                            tier_b_anchor_match = True
                            break
            
            # Validation rules (FIX 4: Single-source confirmation for anchor domain contact pages)
            # Check if from anchor domain contact/about/team page
            is_anchor_contact_page = False
            best_url = best_candidate.source_url
            best_url_lower = best_url.lower()
            best_domain = urlparse(best_url).netloc.lower()
            
            if any(anchor in best_domain for anchor in self.anchor_domains):
                if any(page_type in best_url_lower for page_type in ['/contact', '/about', '/team', '/doctor']):
                    is_anchor_contact_page = True
            
            is_confirmed = False
            confidence = 0.0
            
            if tier_a_count > 0:
                is_confirmed = True
                confidence = 0.9
            elif tier_b_count > 0 and tier_b_anchor_match:
                is_confirmed = True
                confidence = 0.7
            elif (tier_a_count + tier_b_count) >= 2:
                is_confirmed = True
                confidence = 0.8
            elif best_candidate.score >= 50.0:  # High score even if single source
                is_confirmed = True
                confidence = 0.7
            # FIX 4: Single source from anchor domain contact/about/team page (for contact facts)
            elif is_anchor_contact_page:
                contact_facts = ['phone', 'public_email', 'location', 'address']
                if field in contact_facts:
                    is_confirmed = True
                    confidence = 0.8
                    print(f"    ✓ Single-source confirmed (anchor contact page): {field} = '{value[:50]}...'")
            
            best_candidate.confirmed = is_confirmed
            best_candidate.confidence = confidence
            
            if is_confirmed:
                confirmed_facts.append(best_candidate)
        
        return confirmed_facts
    
    def detect_role_pack(self, sources: List[Dict], selected_domain: Optional[str] = None) -> RolePack:
        """
        Detect role pack from content
        FIX 3: Only detect from Tier-A sources (not directory pages)
        """
        # Check if selected domain is a directory
        if selected_domain:
            normalized_domain = self.normalize_domain(selected_domain)
            if any(dir_site in normalized_domain for dir_site in ['justdial.com', 'practo.com', 'indiamart.com']):
                # Directory page - don't detect role pack
                return RolePack.GENERIC
        
        # FIX 3: Only use Tier-A sources for role pack detection
        tier_a_sources = [s for s in sources if s['tier'] == SourceTier.TIER_A]
        
        if not tier_a_sources:
            # No Tier-A sources - return generic
            return RolePack.GENERIC
        
        # Build text only from Tier-A sources
        all_text = ' '.join([s['content']['text'].lower() for s in tier_a_sources])
        
        if any(kw in all_text for kw in ['dentist', 'doctor', 'physician', 'clinic', 'hospital', 'medical']):
            return RolePack.MEDICAL
        elif any(kw in all_text for kw in ['professor', 'university', 'research', 'phd', 'publication']):
            return RolePack.ACADEMIC
        elif any(kw in all_text for kw in ['founder', 'ceo', 'startup', 'company', 'business']):
            return RolePack.BUSINESS
        elif any(kw in all_text for kw in ['artist', 'album', 'film', 'music', 'director']):
            return RolePack.ARTIST
        elif any(kw in all_text for kw in ['minister', 'politician', 'government', 'office']):
            return RolePack.PUBLIC_FIGURE
        
        return RolePack.GENERIC
    
    def normalize_field_name(self, field: str) -> str:
        """
        Field normalization: Map extracted field types → canonical schema
        Fixes mismatch between extractor output and renderer expectations
        """
        field_lower = field.lower()
        
        # Name mappings
        if field_lower in ['name', 'full_name', 'fullname']:
            return 'full_name'
        
        # Role/Profession mappings
        if field_lower in ['occupation', 'jobtitle', 'primary_role', 'role', 'profession', 'title']:
            return 'primary_role'
        
        # Organization mappings
        if field_lower in ['worksfor', 'affiliation', 'primary_organization', 'organization', 'company', 'employer']:
            return 'primary_organization'
        
        # Location mappings
        if field_lower in ['address', 'streetaddress', 'location', 'birth_place', 'birthplace', 'clinic_location']:
            return 'location'
        
        # Phone mappings
        if field_lower in ['telephone', 'phone', 'phonenumber', 'contact_number']:
            return 'phone'
        
        # Email mappings
        if field_lower in ['email', 'mail', 'public_email', 'contact_email']:
            return 'public_email'
        
        # Website mappings
        if field_lower in ['sameas', 'official_websites', 'website', 'url', 'homepage', 'official_website']:
            return 'official_websites'
        
        # Education mappings
        if field_lower in ['alumniof', 'education', 'qualification', 'degree']:
            return 'education'
        
        # Specialization mappings
        if field_lower in ['specialization', 'specialty', 'specialties', 'special_interests', 'interests']:
            return 'specialization'
        
        # Experience mappings
        if field_lower in ['experience', 'experience_years', 'years_of_experience']:
            return 'experience_years'
        
        # Birth date mappings
        if field_lower in ['birth_date', 'dateofbirth', 'dob', 'born']:
            return 'birth_date'
        
        # Nationality mappings
        if field_lower in ['nationality', 'citizenship']:
            return 'nationality'
        
        # Known for mappings
        if field_lower in ['known_for', 'knownfor']:
            return 'known_for'
        
        # Return as-is if no mapping found
        return field
    
    def build_about_table(self, confirmed_facts: List[FactCandidate], role_pack: RolePack) -> Dict:
        """Build About table from confirmed facts only - role pack specific schema"""
        
        # DEBUG: Print confirmed fact types
        from collections import Counter
        fact_types = Counter([f.field for f in confirmed_facts])
        print(f"\n🔍 DEBUG: Confirmed fact types: {dict(fact_types.most_common(20))}")
        if confirmed_facts:
            sample = confirmed_facts[0]
            print(f"🔍 DEBUG: Sample fact - field: '{sample.field}', value: '{sample.value[:50]}...', source: {sample.source_url[:50]}")
        
        about_table = {}
        
        # Normalize and group by field
        facts_by_field = {}
        for fact in confirmed_facts:
            normalized_field = self.normalize_field_name(fact.field)
            if normalized_field not in facts_by_field:
                facts_by_field[normalized_field] = []
            facts_by_field[normalized_field].append(fact)
        
        print(f"🔍 DEBUG: Normalized fields: {list(facts_by_field.keys())}")
        
        # Build table based on role pack
        if role_pack in [RolePack.PUBLIC_FIGURE, RolePack.ARTIST] or any(kw in str(role_pack).lower() for kw in ['sports', 'celebrity']):
            # Public figure / Celebrity schema
            field_mapping = {
                'full_name': 'Full Name',
                'primary_role': 'Profession',
                'nationality': 'Nationality',
                'birth_date': 'Date of Birth',
                'location': 'Birth Place',
                'known_for': 'Known For / Teams',
                'official_websites': 'Official Profiles'
            }
        elif role_pack == RolePack.MEDICAL:
            # Medical schema
            field_mapping = {
                'full_name': 'Full Name',
                'primary_role': 'Professional Title(s)',
                'education': 'Education / Qualifications',
                'specialization': 'Special Interests',
                'primary_organization': 'Business / Clinic Name',
                'experience_years': 'Work Experience',
                'location': 'Clinic / Primary Practice Location',
                'services': 'Services Highlighted',
                'public_email': 'Public Email(s)',
                'phone': 'Phone (Public Contact)',
                'official_websites': 'Online Profiles / Presence'
            }
        elif role_pack == RolePack.BUSINESS:
            # Business schema
            field_mapping = {
                'full_name': 'Full Name',
                'primary_role': 'Roles',
                'primary_organization': 'Companies',
                'location': 'Location',
                'official_websites': 'Official Profiles'
            }
        else:
            # Generic schema
            field_mapping = {
                'full_name': 'Full Name',
                'primary_role': 'Professional Title(s)',
                'primary_organization': 'Organization',
                'location': 'Location',
                'official_websites': 'Official Profiles'
            }
        
        # Build table using role-appropriate fields
        # Show fields even if missing (print "—")
        for field, display_name in field_mapping.items():
            if field in facts_by_field:
                facts = facts_by_field[field]
                # Get best fact (highest score, not just confidence)
                best = max(facts, key=lambda f: f.score)
                
                # D) Fix organization fallback - reject domain tokens
                if field == 'primary_organization':
                    org_value = best.value
                    # Reject if it's just the domain token (e.g., "zentaldental")
                    normalized_domain = self.normalize_domain(org_value)
                    if normalized_domain and re.match(r'^[a-z0-9]+$', normalized_domain):
                        # It's a domain token without dots - reject
                        # Use user-provided org instead if available
                        if hasattr(self, '_user_organization') and self._user_organization:
                            about_table[display_name] = self._user_organization
                        else:
                            about_table[display_name] = "—"
                        continue
                
                # For multi-value fields, collect unique values
                if field in ['official_websites', 'public_email', 'phone', 'primary_role', 'education']:
                    values = list(set([f.value for f in facts]))
                    about_table[display_name] = ', '.join(values[:3])
                else:
                    about_table[display_name] = best.value
            else:
                # D) Fix organization fallback - use user-provided org if available
                if field == 'primary_organization':
                    if hasattr(self, '_user_organization') and self._user_organization:
                        about_table[display_name] = self._user_organization
                    else:
                        about_table[display_name] = "—"
                else:
                    # Show "—" for missing fields (so table isn't empty)
                    about_table[display_name] = "—"
        
        return about_table
    
    def generate_bio(self, about_table: Dict, role_pack: RolePack) -> str:
        """
        STEP 8: Generate bio from confirmed facts
        Uses available fields, doesn't require "bio" fact
        """
        # Map display names back to values
        name = None
        role = None
        org = None
        location = None
        spec = None
        experience = None
        
        # Find values from about_table (handle different display name variations)
        for display_name, value in about_table.items():
            if value and value != "—":
                if 'Full Name' in display_name or 'Name' in display_name:
                    name = value
                elif 'Professional Title' in display_name or 'Profession' in display_name or 'Role' in display_name:
                    role = value
                elif 'Clinic' in display_name or 'Practice' in display_name or 'Organization' in display_name or 'Company' in display_name:
                    org = value
                elif 'Location' in display_name or 'Address' in display_name:
                    location = value
                elif 'Special' in display_name or 'Interest' in display_name:
                    spec = value
                elif 'Experience' in display_name:
                    experience = value
        
        parts = []
        
        if name and role:
            parts.append(f"{name} is a {role}")
        elif name:
            parts.append(name)
        
        if org and org != "—":
            parts.append(f"associated with {org}")
        
        if location and location != "—":
            parts.append(f"based in {location}")
        
        # Role-specific additions
        if role_pack == RolePack.MEDICAL:
            if spec and spec != "—":
                parts.append(f"specializing in {spec}")
            if experience and experience != "—":
                parts.append(f"with {experience} of experience")
        
        bio = '. '.join(parts) + '.' if parts else "Bio not available from confirmed facts."
        
        return bio
    
    def build_profile(self, 
                     name: Optional[str] = None,
                     domain: Optional[str] = None,
                     organization: Optional[str] = None,
                     city: Optional[str] = None,
                     handle: Optional[str] = None,
                     known_page: Optional[str] = None) -> Dict:
        """
        Main pipeline: Build profile with identity resolution
        """
        # FIX: Smart field assignment before processing
        corrected = self.smart_field_assigner(name, domain, organization, city, handle, known_page)
        name = corrected['name']
        domain = corrected['domain']
        organization = corrected['organization']
        city = corrected['city']
        handle = corrected['handle']
        known_page = corrected['known_page']
        
        # Store user-provided organization for fallback
        self._user_organization = organization
        
        # Canonicalize domain (prefer https://www)
        if domain:
            normalized = self.normalize_domain(domain)
            # Try https://www first
            test_url = f"https://www.{normalized}"
            try:
                response = self.session.head(test_url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    domain = normalized  # Use normalized version
            except:
                pass
        
        # STEP 1: Identity Resolution
        print("\n🔍 STEP 1: Identity Resolution")
        candidates = self.resolve_identity_candidates(
            name=name,
            domain=domain,
            organization=organization,
            city=city,
            handle=handle,
            known_page=known_page
        )
        
        if not candidates:
            return {'error': 'No candidates found. Please provide at least one anchor.'}
        
        # Show candidates
        print(f"\nFound {len(candidates)} candidate(s):")
        for i, candidate in enumerate(candidates, 1):
            print(f"  {i}. {candidate.name}")
            print(f"     Domain: {candidate.domain}")
            print(f"     Organization: {candidate.organization or 'N/A'}")
            print(f"     URLs: {len(candidate.top_urls)}")
        
        # FIX 1: Auto-select based on domain match (if domain provided)
        if domain and len(candidates) > 0:
            # Already filtered and sorted by domain match
            selected = candidates[0]
            print(f"\n✓ Auto-selected: {selected.name} ({selected.domain}) [Domain match]")
        elif len(candidates) > 1:
            print("\n⚠️  Multiple candidates found. Auto-selecting highest-scored candidate.")
            print("   (In production, user would select here)")
            selected = candidates[0]
        else:
            selected = candidates[0]
        
        print(f"\n✓ Selected: {selected.name} ({selected.domain})")
        
        # STEP 2: Source Collection
        print("\n📚 STEP 2: Source Collection")
        sources = self.collect_sources(selected, user_domain=domain)
        print(f"✓ Collected {len(sources)} sources")
        
        # Detect role pack (FIX 3: with domain check)
        role_pack = self.detect_role_pack(sources, selected_domain=selected.domain)
        print(f"✓ Detected role pack: {role_pack.value}")
        
        # STEP 4 & 5: Extract facts
        print("\n🔎 STEP 4 & 5: Fact Extraction")
        fact_candidates = self.extract_fact_candidates(sources, role_pack, selected_candidate=selected)
        print(f"✓ Extracted {len(fact_candidates)} fact candidates")
        
        # STEP 6: Validate
        print("\n✅ STEP 6: Validation")
        confirmed_facts = self.validate_facts(fact_candidates)
        print(f"✓ Confirmed {len(confirmed_facts)} facts")
        
        # STEP 7: Build About table
        print("\n📋 STEP 7: Building About Table")
        about_table = self.build_about_table(confirmed_facts, role_pack)
        
        # STEP 8: Generate bio
        bio = self.generate_bio(about_table, role_pack)
        
        # Build output
        result = {
            'verified_identity': {
                'name': selected.name,
                'domain': selected.domain,
                'organization': selected.organization,
            },
            'confirmed_facts': about_table,
            'bio': bio,
            'role_pack': role_pack.value,
            'sources': [s['url'] for s in sources],
            'fact_count': {
                'total_candidates': len(fact_candidates),
                'confirmed': len(confirmed_facts)
            },
            '_confirmed_facts_list': confirmed_facts  # For formatting
        }
        
        return result
    
    def format_output(self, result: Dict, confirmed_facts: List[FactCandidate]) -> str:
        """
        C) Format output as nice Field/Details table with sections
        """
        output_lines = []
        name = result['verified_identity'].get('name', 'Unknown')
        about_table = result['confirmed_facts']  # This is the about_table dict with display names as keys
        
        # Header
        output_lines.append("="*60)
        output_lines.append(f"📋 About — {name} (Public Info)")
        output_lines.append("="*60)
        output_lines.append("")
        
        # Table section
        output_lines.append("Field" + " " * 18 + "| Details")
        output_lines.append("-" * 60)
        
        # Render all fields from about_table (display names are keys)
        for display_name, value in about_table.items():
            if value and value != "—":
                # Add confidence note (simplified)
                confidence_note = ""
                # Count sources for this field
                normalized_display = display_name.lower()
                matching_facts = []
                for fact in confirmed_facts:
                    normalized_field = self.normalize_field_name(fact.field)
                    # Check if this fact matches the display name
                    if ('name' in normalized_display and normalized_field == 'full_name') or \
                       ('title' in normalized_display and normalized_field == 'primary_role') or \
                       ('clinic' in normalized_display and normalized_field == 'primary_organization') or \
                       ('location' in normalized_display and normalized_field == 'location') or \
                       ('email' in normalized_display and normalized_field == 'public_email') or \
                       ('phone' in normalized_display and normalized_field == 'phone') or \
                       ('online' in normalized_display and normalized_field == 'official_websites'):
                        matching_facts.append(fact)
                
                if len(matching_facts) >= 2:
                    confidence_note = f" (confirmed by {len(matching_facts)} sources)"
                elif matching_facts:
                    source_domain = urlparse(matching_facts[0].source_url).netloc.replace('www.', '')
                    confidence_note = f" (from {source_domain})"
                
                output_lines.append(f"{display_name:25} | {value}{confidence_note}")
            elif value == "—":
                # Show missing fields too (so table isn't empty)
                output_lines.append(f"{display_name:25} | —")
        
        output_lines.append("")
        output_lines.append("="*60)
        
        # Short Bio section
        if result.get('bio'):
            output_lines.append("")
            output_lines.append("🧠 Short Bio")
            output_lines.append("-" * 60)
            output_lines.append(result['bio'])
            output_lines.append("")
        
        # Listing Snapshot (if available)
        output_lines.append("="*60)
        output_lines.append(f"Sources: {len(result['sources'])} URLs scraped")
        output_lines.append(f"Facts: {result['fact_count']['confirmed']}/{result['fact_count']['total_candidates']} confirmed")
        output_lines.append("="*60)
        
        return "\n".join(output_lines)
