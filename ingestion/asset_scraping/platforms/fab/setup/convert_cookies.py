import json

# PASTE YOUR COPIED COOKIE HEADER STRING BELOW (Inside the quotes)
RAW_COOKIE_STRING = """
cf_clearance=OAkhMWTsQg87AoOT2ZQP0JPJvdM1jcGqZbU7TQtGgwY-1765748951-1.2.1.1-DQj3ffRz74u6XXESp._0njdTPXRVnaQ2X5hCBZ2DSF53uVpSvi7R0Dp35ZOGBNZMXGCGEV5ZBYIqy0WT1rAt.NuSFOuvKnsEf43vVyEuaHIsHiJbcAzuxVglGErANpacERTHk48v2Xr8upcgKsWdHbTbhZ_eyHVF_oxak49ps9sCNuGx_o_JjwCLw4jS3Kl5A0Kd9nrlnN9yZfC1y.7Ljyu5z1bCdyZC7pvTeMd4R74; fab_csrftoken=m5d3QjPi3DPEGo6ZJJY9jeAIl6qxAg9O; fab_sessionid=2ywv7hppiwthvivs2uronfw1gwhpexk8; __cf_bm=k5.QOAFNCfmdDwLQSoyNv0Dpi3oUnDPSOlJbUCtz5bI-1765750101-1.0.1.1-8bwjby5oI40RFiNyH2hSh_9mfnnD.EdFqt.xzDeZt9L7vvuNtELepRQ6QKSmKnuCGGSC4cj2laUZEEudT_PzZ2uCHii6786Pd0sBe4JFpXw
"""

def create_auth_json():
    cookies = []
    
    # Simple parser for the raw cookie string
    # Format: "key=value; key2=value2; ..."
    if not RAW_COOKIE_STRING.strip() or "PASTE_HERE" in RAW_COOKIE_STRING:
        print("Error: You didn't paste the cookie string into the script!")
        return

    pairs = RAW_COOKIE_STRING.split(';')
    
    for pair in pairs:
        if '=' not in pair:
            continue
            
        name, value = pair.split('=', 1)
        name = name.strip()
        value = value.strip()
        
        # We assume strict security to match Epic's requirements
        cookie_obj = {
            "name": name,
            "value": value,
            "domain": ".fab.com",  # Wildcard domain covers subdomains
            "path": "/",
            "expires": -1, # Session cookie
            "httpOnly": False, # Playwright doesn't strictly enforce this on injection
            "secure": True,
            "sameSite": "None"
        }
        cookies.append(cookie_obj)

    # Playwright storageState format
    auth_data = {
        "cookies": cookies,
        "origins": [] # LocalStorage is likely not strictly required for auth, just UI state
    }

    with open("auth.json", "w") as f:
        json.dump(auth_data, f, indent=2)
    
    print(f"✅ Successfully converted {len(cookies)} cookies to 'auth.json'")

if __name__ == "__main__":
    create_auth_json()