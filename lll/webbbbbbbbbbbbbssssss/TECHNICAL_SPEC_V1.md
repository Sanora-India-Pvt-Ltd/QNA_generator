# Weighted Scoring Model - Version 1
## Technical Specification (Engineer-Ready)

**Version:** 1.0  
**Type:** Deterministic Rule-Based Scoring Engine  
**Status:** Implementation Ready  
**Complexity:** Low-Medium (No ML Required)

---

## 🎯 Executive Summary

This is a **deterministic weighted scoring system**, not a machine learning model. It uses:
- Fixed weight buckets
- Arithmetic calculations
- Confidence multipliers
- Static lookup tables
- Config-driven rules

**No neural networks, no training data, no predictions required for V1.**

---

## 📋 System Architecture

### Core Components

1. **Input Data Handler** - Accepts declared + verified fields
2. **Weight Calculator** - Applies bucket weights to inputs
3. **Confidence Multiplier** - Adjusts score based on verification status
4. **PIN Wealth Index** - Static lookup table for residence scoring
5. **Score Aggregator** - Combines all components into final score
6. **Audit Logger** - Records all calculations for explainability

---

## 📥 Input Schema

### Declared Fields (User-Provided)
```json
{
  "age_band": "25-35",
  "profession": "Software Engineer",
  "employment_type": "Salaried",
  "pin_code": "110016",
  "phone_type": "Smartphone",
  "years_of_experience": 5
}
```

### Verified Fields (Document-Based, Optional)
```json
{
  "pan_verified": true,
  "itr_verified": true,
  "gst_verified": false,
  "degree_verified": true,
  "verification_date": "2024-01-15"
}
```

### Public Signals (Web-Scraped, Optional)
```json
{
  "google_rating": 4.5,
  "review_count": 120,
  "linkedin_presence": true,
  "business_registration": true
}
```

---

## 🎚️ Weight Buckets (Fixed Configuration)

| Bucket | Max Weight | Description |
|--------|-----------|-------------|
| **Profession & Employment** | 30 | Job title, employment type, industry |
| **Income & Financial** | 25 | Income band, financial documents |
| **Business Experience** | 15 | Years in business, business type |
| **Residence / PIN Wealth** | 10 | PIN code wealth index |
| **Social Proof** | 10 | Ratings, reviews, online presence |
| **Assets & Lifestyle** | 10 | Property ownership, lifestyle indicators |

**Total Maximum Score (before multiplier): 100**

---

## 🔢 Scoring Rules

### 1. Profession & Employment (Max: 30 points)

**Sub-components:**
- Profession category: 0-15 points
- Employment type: 0-10 points
- Industry stability: 0-5 points

**Scoring Table:**
```json
{
  "profession_categories": {
    "Doctor": 15,
    "Engineer": 12,
    "Lawyer": 12,
    "CA/Accountant": 11,
    "Teacher": 8,
    "Business Owner": 10,
    "Government Employee": 9,
    "Other": 5
  },
  "employment_types": {
    "Salaried (MNC)": 10,
    "Salaried (Indian Company)": 8,
    "Self-Employed (Verified)": 9,
    "Business Owner (Verified)": 10,
    "Freelancer": 6,
    "Unemployed": 0
  }
}
```

### 2. Income & Financial (Max: 25 points)

**Scoring:**
- Income band: 0-15 points
- Document verification bonus: 0-10 points

**Income Bands:**
```json
{
  "income_bands": {
    "50L+": 15,
    "25L-50L": 12,
    "15L-25L": 10,
    "10L-15L": 8,
    "5L-10L": 5,
    "Below 5L": 2
  },
  "verification_bonus": {
    "ITR_verified": 5,
    "GST_verified": 3,
    "Bank_statement_verified": 2
  }
}
```

### 3. Business Experience (Max: 15 points)

**Scoring:**
```json
{
  "years_in_business": {
    "10+": 15,
    "5-10": 12,
    "3-5": 8,
    "1-3": 5,
    "0-1": 2
  }
}
```

### 4. Residence / PIN Wealth Index (Max: 10 points)

**Uses static lookup table:**
```json
{
  "pin_wealth_index": {
    "premium": 10,
    "upper_middle": 7,
    "middle": 5,
    "lower_middle": 3,
    "basic": 1
  }
}
```

**PIN codes mapped to categories (separate file - see `pin_wealth_index.json`)**

### 5. Social Proof (Max: 10 points)

**Scoring:**
```json
{
  "google_rating": {
    "4.5+": 5,
    "4.0-4.5": 3,
    "3.5-4.0": 1,
    "Below 3.5": 0
  },
  "review_count": {
    "100+": 3,
    "50-100": 2,
    "10-50": 1,
    "Below 10": 0
  },
  "linkedin_presence": 2
}
```

### 6. Assets & Lifestyle (Max: 10 points)

**Scoring:**
```json
{
  "property_ownership": {
    "Owns property (verified)": 7,
    "Rents premium": 3,
    "Rents standard": 1,
    "Unknown": 0
  },
  "phone_type": {
    "Premium smartphone": 2,
    "Standard smartphone": 1,
    "Basic phone": 0
  },
  "vehicle_ownership": {
    "Premium vehicle": 1,
    "Standard vehicle": 0.5,
    "None": 0
  }
}
```

---

## ✨ Confidence Multiplier

**Critical for legal compliance and fraud prevention:**

```json
{
  "confidence_multipliers": {
    "all_verified": 1.0,
    "partial_verified": 0.8,
    "declared_only": 0.6,
    "no_documents": 0.4
  }
}
```

**Calculation Logic:**
- If PAN + ITR verified: `all_verified` (1.0)
- If only PAN verified: `partial_verified` (0.8)
- If only declared data: `declared_only` (0.6)
- If no documents provided: `no_documents` (0.4)

---

## 🧮 Final Score Calculation

```
Raw Score = 
  Profession_Score (max 30) +
  Income_Score (max 25) +
  Business_Score (max 15) +
  Residence_Score (max 10) +
  Social_Score (max 10) +
  Assets_Score (max 10)

Final Score = Raw Score × Confidence_Multiplier

Final Score Range: 0-100
```

---

## 📊 Output Schema

```json
{
  "user_id": "user_12345",
  "timestamp": "2024-01-15T10:30:00Z",
  "final_score": 72.5,
  "raw_score": 90.0,
  "confidence_multiplier": 0.8,
  "score_breakdown": {
    "profession": {
      "score": 25,
      "max": 30,
      "details": {
        "profession_category": "Engineer",
        "employment_type": "Salaried (MNC)",
        "points_breakdown": {
          "profession": 12,
          "employment": 10,
          "industry_stability": 3
        }
      }
    },
    "income": {
      "score": 20,
      "max": 25,
      "details": {
        "income_band": "15L-25L",
        "verification_bonus": 5
      }
    },
    "business": {
      "score": 12,
      "max": 15,
      "details": {
        "years_in_business": "5-10"
      }
    },
    "residence": {
      "score": 10,
      "max": 10,
      "details": {
        "pin_code": "110016",
        "wealth_category": "premium"
      }
    },
    "social": {
      "score": 8,
      "max": 10,
      "details": {
        "google_rating": 4.6,
        "review_count": 150,
        "linkedin_presence": true
      }
    },
    "assets": {
      "score": 5,
      "max": 10,
      "details": {
        "property_ownership": "Rents premium",
        "phone_type": "Premium smartphone"
      }
    }
  },
  "verification_status": {
    "pan_verified": true,
    "itr_verified": true,
    "gst_verified": false,
    "confidence_level": "partial_verified"
  },
  "audit_trail": {
    "calculation_version": "v1.0",
    "config_version": "2024-01-15",
    "calculation_steps": [
      "Input validation: PASSED",
      "Profession scoring: 25/30",
      "Income scoring: 20/25",
      "..."
    ]
  }
}
```

---

## 🔒 Legal & Compliance Requirements

1. **Explainability**: Every score must be explainable with audit trail
2. **No Bias**: All rules are deterministic and transparent
3. **Data Privacy**: Only use declared + verified + public data
4. **Audit Logging**: All calculations logged with timestamps
5. **Version Control**: Config changes tracked and versioned

---

## 🚀 Implementation Requirements

### Technology Stack (Recommended)
- **Language**: Python 3.9+ or Node.js 18+
- **Framework**: FastAPI (Python) or Express (Node.js)
- **Database**: PostgreSQL for audit logs
- **Config**: JSON files (version-controlled)
- **Testing**: Unit tests for all scoring rules

### API Endpoints

```
POST /api/v1/score/calculate
GET  /api/v1/score/{user_id}
GET  /api/v1/score/{user_id}/breakdown
GET  /api/v1/score/{user_id}/audit
```

### Performance Requirements
- Response time: < 200ms (excluding external API calls)
- Concurrent requests: 1000+
- Uptime: 99.9%

---

## 📝 Testing Requirements

1. **Unit Tests**: Each scoring bucket tested independently
2. **Integration Tests**: End-to-end scoring with sample data
3. **Edge Cases**: Missing fields, invalid inputs, boundary values
4. **Regression Tests**: Config changes don't break existing scores

---

## 🔄 Version Control

- Config files versioned with dates
- Score calculation version tracked in output
- Backward compatibility maintained for 6 months

---

## 📈 Future Enhancements (V2+)

- ML-based PIN clustering (optional)
- Fraud anomaly detection (optional)
- Dynamic weight adjustment (optional)
- **V1 remains rule-based and explainable**

---

## ✅ Acceptance Criteria

This spec is complete when:
- [ ] All weight buckets defined in JSON config
- [ ] PIN wealth index lookup table created
- [ ] Confidence multiplier logic implemented
- [ ] API returns explainable score breakdown
- [ ] Audit logging functional
- [ ] Unit tests passing
- [ ] Documentation complete

---

**This is a PRODUCT ENGINEERING task, not an ML research task.**
