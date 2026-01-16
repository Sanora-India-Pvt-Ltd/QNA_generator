from datetime import datetime
import json
import os

CONSENT_FILE = "data/consents.json"


def _ensure_storage():
    """Ensure consent storage file exists."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(CONSENT_FILE):
        with open(CONSENT_FILE, "w") as f:
            json.dump([], f)


def save_consent(user_name: str, scope: str = "public_web_only"):
    """
    Save user consent with timestamp.
    """
    _ensure_storage()

    consent_record = {
        "user_name": user_name,
        "scope": scope,
        "consent": True,
        "timestamp": datetime.utcnow().isoformat()
    }

    with open(CONSENT_FILE, "r") as f:
        data = json.load(f)

    data.append(consent_record)

    with open(CONSENT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return consent_record


def has_valid_consent(user_name: str) -> bool:
    """
    Check if valid consent exists for the user.
    """
    if not os.path.exists(CONSENT_FILE):
        return False

    with open(CONSENT_FILE, "r") as f:
        data = json.load(f)

    for record in data:
        if record["user_name"].lower() == user_name.lower() and record["consent"]:
            return True

    return False
