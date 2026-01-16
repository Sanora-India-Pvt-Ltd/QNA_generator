"""
Identity Fingerprint Configurations
Add custom identity fingerprints for specific people here
"""

from scraper import IdentityFingerprint

# Example: Dr. Sanjay Arora (TMJ Dentist)
DR_SANJAY_ARORA_FINGERPRINT = IdentityFingerprint(
    allowed_domains=[
        'zentaldental.com',
        'tmjhelpline.com',
        'tmjhelpline.in',
        'bodypainshelpline.com'
    ],
    cities=['new delhi', 'delhi', 'green park', 'saket', 'south delhi'],
    specialty_keywords=['dentist', 'endodontist', 'tmj', 'occlusion', 'dental', 'cranio-sacral'],
    clinic_keywords=['zental', 'tmj helpline', 'body pain', 'swaran dental'],
    required_matches=2
)

# Add more identity fingerprints here as needed
# Example:
# JOHN_DOE_FINGERPRINT = IdentityFingerprint(
#     allowed_domains=['johndoe.com'],
#     cities=['mumbai'],
#     specialty_keywords=['engineer', 'software'],
#     clinic_keywords=['tech corp'],
#     required_matches=2
# )

# Mapping function
def get_identity_fingerprint(person_name: str) -> IdentityFingerprint:
    """Get identity fingerprint for a person"""
    name_lower = person_name.lower()
    
    if "sanjay arora" in name_lower and "dr" in name_lower:
        return DR_SANJAY_ARORA_FINGERPRINT
    
    # Add more mappings here
    # if "john doe" in name_lower:
    #     return JOHN_DOE_FINGERPRINT
    
    return None
