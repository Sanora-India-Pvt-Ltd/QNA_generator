import json

with open("config/templates.json") as f:
    TEMPLATES = json.load(f)

def build_about_table(req, fields):
    specialization = ", ".join(
        set(v["value"] for v in fields.get("specialization", []))
    ) or "public clinical practice"

    about = [
        {"field": "Full Name", "value": req.name},
        {"field": "Profession", "value": req.profession},
        {"field": "Public Email", "value": req.email},
        {"field": "Specialization", "value": specialization}
    ]

    bio = TEMPLATES["short_bio"].format(
        name=req.name,
        profession=req.profession,
        specialization=specialization
    )

    return {
        "about_table": about,
        "short_bio": bio,
        "disclaimer": "All information is compiled from publicly available sources."
    }
