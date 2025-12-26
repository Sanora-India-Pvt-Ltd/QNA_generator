import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("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")

print("KEY FOUND:", key is not None)
print("KEY LENGTH:", len(key) if key else None)
print("KEY PREFIX:", key[:10] if key else None)
