import json

with open("config/field_rules.json") as f:
    RULES = json.load(f)

def extract_fields(pages):
    extracted = {}

    for page in pages:
        text = page["text"]
        url = page["url"]

        for field, keywords in RULES.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    extracted.setdefault(field, []).append({
                        "value": kw,
                        "source": url
                    })

    return extracted
