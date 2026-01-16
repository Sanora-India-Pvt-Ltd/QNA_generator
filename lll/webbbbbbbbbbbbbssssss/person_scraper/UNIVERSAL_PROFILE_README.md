# Universal Profile Builder

**Never builds from name only** - requires at least one anchor to prevent identity collisions.

## 🔥 Core Principle

**Universal Rule:** Never build a profile from "name only."
Always require at least 1 anchor (domain, organization, city, handle, or official page).

If user gives only a name → system returns 2–5 candidates first, then user picks.

---

## 📋 Pipeline (8 Steps)

### STEP 1 — Identity Resolution (Candidate → Select)

**Inputs accepted (any 1–2 of these):**
- ✅ Official website / domain (best)
- ✅ Employer / organization (company, university, hospital)
- ✅ City / country
- ✅ Unique handle (X/Twitter, GitHub)
- ✅ Known page (Wikipedia, Google Scholar, Crunchbase)

**Output:**
- Candidate list (2–5)
  - name
  - domain
  - org
  - location hint
  - top 1–2 URLs
- User selects the correct candidate → proceed

---

### STEP 2 — Source Collection (Universal Source Tiers)

Collect sources in tiers (accuracy stays high):

**Tier A (highest trust):**
- Official websites (personal/company/university)
- Government / institutional pages
- Verified directories (Google Business Profile, professional registries)
- Reputable news outlets

**Tier B (medium trust):**
- Conference speaker bios
- Award pages
- Publisher pages (book author pages)
- Podcast/show pages

**Tier C (use as hints, don't scrape deeply):**
- LinkedIn, Instagram, Facebook (often login/UI junk)
- X profiles (public, but limited structured data)

**Rule:** Facts from Tier C must be confirmed by Tier A/B to become "confirmed".

---

### STEP 3 — Main Content Extraction

Before extracting facts, clean HTML:
- Remove nav, header, footer, aside, script, style
- Use readability-like extraction if possible
- Keep evidence snippets (exact text spans)

---

### STEP 4 — Universal Fact Types (Schema)

Use one schema that works for everyone:

**Core Identity:**
- Full Name
- Known As / Aliases
- Primary Role / Title
- Primary Organization
- Location (city/country)

**Professional:**
- Industry / Domain (health, tech, academia, arts)
- Current Position(s)
- Past Positions
- Experience (years / timeline)
- Credentials

**Education:**
- Education
- Certifications / Licenses (if applicable)
- Memberships (professional bodies)

**Work & Output (choose based on role):**
- Companies founded / invested
- Publications / patents
- Notable works (films, books, albums)
- Research areas / specialties
- Products / projects

**Public Contact & Presence:**
- Official websites
- Public email(s)
- Public phone(s)
- Social links (handles)
- Business listings

**Recognition:**
- Awards / honors
- Media mentions

**Bio:**
- 3–4 lines derived from confirmed facts only

---

### STEP 5 — Extraction Rules (Universal, not job-specific)

Field-by-field extraction, using patterns:

- **Name:** page title / about header / structured data (schema.org Person)
- **Role/Title:** "CEO", "Professor", "Dentist", "Founder" near name or in structured blocks
- **Organization:** "at X", "of X", employer section
- **Location:** address blocks, "Based in", structured data, business listing
- **Education:** "BSc", "MBA", "PhD", "MD", "MDS", etc. only if explicitly stated
- **Experience:** "X years", or timeline ranges
- **Awards:** "Award", "Honored", "Winner" sections
- **Contacts:** from explicit "Contact" sections only

**Hard rule:** If a field isn't explicitly present → don't fill it.

---

### STEP 6 — Validation (Stop identity mixing)

A fact becomes **CONFIRMED** only if:

✅ It appears in Tier A  
OR  
✅ It appears in Tier B + matches the anchor (same org/domain/location)  
OR  
✅ It appears in 2 independent sources (A/B)

Otherwise store as:
- `public_mention` (not confirmed)

This prevents "multiple persons same name" from polluting.

---

### STEP 7 — Build Output (Universal About Table)

Output includes:
- **About table** (confirmed facts only)
- **Public mentions** (unconfirmed, with sources)
- **Sources list**
- **Disclaimer**

---

### STEP 8 — Bio Generation (universal template)

Bio template that works for all:

```
{Name} is a {role/title} associated with {org}, based in {location}. 
Their work focuses on {specialties/areas}. They have been recognized 
through {awards/media/pubs}. They maintain a public presence via 
{website/social}.
```

Only plug in fields that are confirmed.

---

## 🎯 Role Packs

After identity resolution, choose a role pack based on detected role keywords:

- **Business/Founder pack** → companies, funding, products
- **Academic pack** → publications, affiliations, research
- **Medical pack** → specialization, clinic, license, services
- **Artist/Creator pack** → works, discography/filmography, tours
- **Public figure pack** → offices, policy roles, speeches

You keep the same schema but prioritize different fields.

---

## 💻 Usage

### Command Line

```bash
cd person_scraper
python universal_main.py
```

Then provide at least one anchor:
- Domain/website
- Organization
- City
- Handle
- Known page URL

### Python API

```python
from universal_profile_builder import UniversalProfileBuilder

builder = UniversalProfileBuilder(api_key, cse_id)

# Must provide at least one anchor
result = builder.build_profile(
    name="Dr. Sanjay Arora",  # Optional
    domain="tmjhelpline.com",  # Best anchor
    organization="Zental Dental",  # Optional
    city="New Delhi"  # Optional
)

print(result['confirmed_facts'])
print(result['bio'])
```

---

## 📊 Output Structure

```json
{
  "verified_identity": {
    "name": "Dr. Sanjay Arora",
    "domain": "tmjhelpline.com",
    "organization": "Zental Dental"
  },
  "confirmed_facts": {
    "full_name": "Dr. Sanjay Arora",
    "primary_role": "Dentist",
    "primary_organization": "Zental Dental",
    "location": "New Delhi",
    "official_websites": "https://tmjhelpline.com",
    "public_email": "tmjhelpline@gmail.com"
  },
  "bio": "Dr. Sanjay Arora is a Dentist associated with Zental Dental, based in New Delhi.",
  "role_pack": "medical",
  "sources": ["https://tmjhelpline.com", "..."],
  "fact_count": {
    "total_candidates": 45,
    "confirmed": 12
  }
}
```

---

## ✅ Key Features

1. **Identity Resolution** - Never mixes identities
2. **Source Tiers** - Trust-based fact validation
3. **Role Packs** - Adapts to different professions
4. **Evidence-Gated** - Every fact has evidence snippet
5. **Confidence Scoring** - Only confirmed facts in output
6. **Universal Schema** - Works for all roles

---

## 🚫 What It Doesn't Do

- ❌ Build from name only
- ❌ Mix identities with same name
- ❌ Include unconfirmed facts in About table
- ❌ Guess or infer missing information
- ❌ Scrape social media deeply (Tier C only)

---

## 🔒 Validation Rules

A fact is confirmed if:
- Appears in Tier A source, OR
- Appears in Tier B + matches anchor, OR
- Appears in 2+ independent sources

Otherwise → stored as public mention (not in About table).

---

**This system prevents identity collisions and ensures accuracy.**
