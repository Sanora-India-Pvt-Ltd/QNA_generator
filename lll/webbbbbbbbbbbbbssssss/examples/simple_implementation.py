"""
Simple Implementation Example - Weighted Scoring Model V1
This demonstrates how straightforward the V1 implementation is.
No ML required - just arithmetic and lookup tables.
"""

import json
from typing import Dict, Any
from datetime import datetime

# Load configuration files
def load_config(filepath: str) -> Dict:
    with open(filepath, 'r') as f:
        return json.load(f)

# Initialize configs (in production, cache these)
WEIGHT_BUCKETS = load_config('config/weight_buckets.json')
CONFIDENCE_MULTIPLIERS = load_config('config/confidence_multipliers.json')
PIN_WEALTH_INDEX = load_config('config/pin_wealth_index.json')

def calculate_profession_score(input_data: Dict) -> Dict:
    """Calculate profession & employment score (max 30)"""
    bucket = WEIGHT_BUCKETS['buckets']['profession_employment']
    
    profession = input_data.get('profession', 'Other')
    employment = input_data.get('employment_type', 'Unknown')
    industry = input_data.get('industry', 'Unknown')
    
    # Lookup scores
    profession_points = bucket['components']['profession_category']['scoring'].get(profession, 5)
    employment_points = bucket['components']['employment_type']['scoring'].get(employment, 0)
    industry_points = bucket['components']['industry_stability']['scoring'].get(industry, 0)
    
    total_score = profession_points + employment_points + industry_points
    
    return {
        'score': total_score,
        'max': bucket['max_weight'],
        'details': {
            'profession': profession_points,
            'employment': employment_points,
            'industry': industry_points
        }
    }

def calculate_income_score(input_data: Dict, verified: Dict) -> Dict:
    """Calculate income & financial score (max 25)"""
    bucket = WEIGHT_BUCKETS['buckets']['income_financial']
    
    income_band = input_data.get('income_band', 'Below 5L')
    income_points = bucket['components']['income_band']['scoring'].get(income_band, 2)
    
    # Verification bonuses
    bonus = 0
    if verified.get('itr_verified'):
        bonus += bucket['components']['verification_bonus']['scoring']['ITR_verified']
    if verified.get('gst_verified'):
        bonus += bucket['components']['verification_bonus']['scoring']['GST_verified']
    if verified.get('bank_statement_verified'):
        bonus += bucket['components']['verification_bonus']['scoring']['Bank_statement_verified']
    
    # Cap bonus at max
    bonus = min(bonus, bucket['components']['verification_bonus']['max'])
    
    total_score = income_points + bonus
    
    return {
        'score': total_score,
        'max': bucket['max_weight'],
        'details': {
            'income_band': income_points,
            'verification_bonus': bonus
        }
    }

def calculate_business_score(input_data: Dict) -> Dict:
    """Calculate business experience score (max 15)"""
    bucket = WEIGHT_BUCKETS['buckets']['business_experience']
    
    years = input_data.get('years_of_experience', 0)
    
    # Map years to band
    if years >= 10:
        band = "10+"
    elif years >= 5:
        band = "5-10"
    elif years >= 3:
        band = "3-5"
    elif years >= 1:
        band = "1-3"
    else:
        band = "0-1"
    
    score = bucket['components']['years_in_business']['scoring'].get(band, 2)
    
    return {
        'score': score,
        'max': bucket['max_weight'],
        'details': {'years_band': band}
    }

def calculate_residence_score(input_data: Dict) -> Dict:
    """Calculate residence/PIN wealth score (max 10)"""
    bucket = WEIGHT_BUCKETS['buckets']['residence_pin_wealth']
    
    pin_code = str(input_data.get('pin_code', ''))
    
    # Lookup PIN in wealth index
    wealth_category = PIN_WEALTH_INDEX['pin_mappings'].get(pin_code, 'basic')
    score = bucket['components']['pin_wealth_category']['scoring'].get(wealth_category, 1)
    
    return {
        'score': score,
        'max': bucket['max_weight'],
        'details': {
            'pin_code': pin_code,
            'wealth_category': wealth_category
        }
    }

def calculate_social_score(public_signals: Dict) -> Dict:
    """Calculate social proof score (max 10)"""
    bucket = WEIGHT_BUCKETS['buckets']['social_proof']
    
    rating = public_signals.get('google_rating', 0)
    review_count = public_signals.get('review_count', 0)
    linkedin = public_signals.get('linkedin_presence', False)
    
    # Rating score
    if rating >= 4.5:
        rating_points = bucket['components']['google_rating']['scoring']['4.5+']
    elif rating >= 4.0:
        rating_points = bucket['components']['google_rating']['scoring']['4.0-4.5']
    elif rating >= 3.5:
        rating_points = bucket['components']['google_rating']['scoring']['3.5-4.0']
    else:
        rating_points = 0
    
    # Review count score
    if review_count >= 100:
        review_points = bucket['components']['review_count']['scoring']['100+']
    elif review_count >= 50:
        review_points = bucket['components']['review_count']['scoring']['50-100']
    elif review_count >= 10:
        review_points = bucket['components']['review_count']['scoring']['10-50']
    else:
        review_points = 0
    
    # LinkedIn score
    linkedin_points = bucket['components']['linkedin_presence']['scoring'].get(str(linkedin).lower(), 0)
    
    total_score = rating_points + review_points + linkedin_points
    
    return {
        'score': total_score,
        'max': bucket['max_weight'],
        'details': {
            'rating': rating_points,
            'reviews': review_points,
            'linkedin': linkedin_points
        }
    }

def calculate_assets_score(input_data: Dict) -> Dict:
    """Calculate assets & lifestyle score (max 10)"""
    bucket = WEIGHT_BUCKETS['buckets']['assets_lifestyle']
    
    property_own = input_data.get('property_ownership', 'Unknown')
    phone_type = input_data.get('phone_type', 'Basic phone')
    vehicle = input_data.get('vehicle_ownership', 'None')
    
    property_points = bucket['components']['property_ownership']['scoring'].get(property_own, 0)
    phone_points = bucket['components']['phone_type']['scoring'].get(phone_type, 0)
    vehicle_points = bucket['components']['vehicle_ownership']['scoring'].get(vehicle, 0)
    
    total_score = property_points + phone_points + vehicle_points
    
    return {
        'score': total_score,
        'max': bucket['max_weight'],
        'details': {
            'property': property_points,
            'phone': phone_points,
            'vehicle': vehicle_points
        }
    }

def get_confidence_multiplier(verified: Dict) -> tuple:
    """Determine confidence multiplier based on verification status"""
    pan_verified = verified.get('pan_verified', False)
    itr_verified = verified.get('itr_verified', False)
    has_declared = verified.get('has_declared_data', True)
    
    if pan_verified and itr_verified:
        level = 'all_verified'
    elif pan_verified:
        level = 'partial_verified'
    elif has_declared:
        level = 'declared_only'
    else:
        level = 'no_documents'
    
    multiplier = CONFIDENCE_MULTIPLIERS['multipliers'][level]['value']
    
    return multiplier, level

def calculate_score(input_data: Dict, verified: Dict, public_signals: Dict) -> Dict:
    """
    Main scoring function - calculates final score
    This is the entire "ML model" - it's just arithmetic!
    """
    # Calculate each bucket score
    profession_score = calculate_profession_score(input_data)
    income_score = calculate_income_score(input_data, verified)
    business_score = calculate_business_score(input_data)
    residence_score = calculate_residence_score(input_data)
    social_score = calculate_social_score(public_signals)
    assets_score = calculate_assets_score(input_data)
    
    # Sum raw score
    raw_score = (
        profession_score['score'] +
        income_score['score'] +
        business_score['score'] +
        residence_score['score'] +
        social_score['score'] +
        assets_score['score']
    )
    
    # Apply confidence multiplier
    multiplier, confidence_level = get_confidence_multiplier(verified)
    final_score = raw_score * multiplier
    
    # Build response
    return {
        'user_id': input_data.get('user_id', 'unknown'),
        'timestamp': datetime.now().isoformat(),
        'final_score': round(final_score, 2),
        'raw_score': raw_score,
        'confidence_multiplier': multiplier,
        'confidence_level': confidence_level,
        'score_breakdown': {
            'profession_employment': profession_score,
            'income_financial': income_score,
            'business_experience': business_score,
            'residence_pin_wealth': residence_score,
            'social_proof': social_score,
            'assets_lifestyle': assets_score
        },
        'verification_status': verified,
        'audit_trail': {
            'calculation_version': 'v1.0',
            'config_version': WEIGHT_BUCKETS['version']
        }
    }

# Example usage
if __name__ == '__main__':
    # Sample input
    input_data = {
        'user_id': 'user_12345',
        'profession': 'Engineer',
        'employment_type': 'Salaried (MNC)',
        'industry': 'Moderate (IT, Manufacturing)',
        'income_band': '15L-25L',
        'years_of_experience': 7,
        'pin_code': '110016',
        'phone_type': 'Premium smartphone',
        'property_ownership': 'Rents premium',
        'vehicle_ownership': 'None'
    }
    
    verified = {
        'pan_verified': True,
        'itr_verified': True,
        'gst_verified': False,
        'has_declared_data': True
    }
    
    public_signals = {
        'google_rating': 4.6,
        'review_count': 150,
        'linkedin_presence': True
    }
    
    # Calculate score
    result = calculate_score(input_data, verified, public_signals)
    
    # Print result
    print(json.dumps(result, indent=2))
    
    print(f"\n✅ Final Score: {result['final_score']}/100")
    print(f"📊 Raw Score: {result['raw_score']}/100")
    print(f"🔒 Confidence: {result['confidence_level']} (×{result['confidence_multiplier']})")
