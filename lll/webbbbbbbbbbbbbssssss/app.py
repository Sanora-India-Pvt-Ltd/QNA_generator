from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.search import google_search
from core.fetcher import fetch_page
from core.parser import extract_main_text
from core.extractor import extract_fields
from core.formatter import build_about_table

app = FastAPI(title="Public About Profile Builder")

class ProfileRequest(BaseModel):
    name: str
    profession: str
    email: str
    consent: bool

@app.post("/build-profile")
def build_profile(req: ProfileRequest):
    if not req.consent:
        raise HTTPException(status_code=403, detail="Consent required")

    urls = google_search(req.name)
    pages = []

    for url in urls:
        html = fetch_page(url)
        if html:
            text = extract_main_text(html)
            pages.append({"url": url, "text": text})

    fields = extract_fields(pages)
    profile = build_about_table(req, fields)

    return profile
