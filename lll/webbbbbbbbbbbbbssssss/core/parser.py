from bs4 import BeautifulSoup

def extract_main_text(html):
    soup = BeautifulSoup(html, "html.parser")

    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""

    return main.get_text(separator=" ", strip=True)
