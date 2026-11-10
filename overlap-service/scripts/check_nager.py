import json
import urllib.request

BASE = "https://date.nager.at/api/v3"
YEAR = 2026
COUNTRIES = ["KR", "ES", "US", "GB"]
EXPECTED = {"date", "localName", "name", "countryCode", "global"}

for code in COUNTRIES:
    url = f"{BASE}/PublicHolidays/{YEAR}/{code}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    missing = EXPECTED - set(data[0]) if data else EXPECTED
    print(f"{code}: {len(data)} holidays, first = {data[0]['date']} {data[0]['name']!r}")
    print(f"    fields present: {sorted(data[0])}")
    print(f"    missing expected fields: {sorted(missing) or 'none'}")
