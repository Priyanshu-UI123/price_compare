from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

# Make sure you have your API key set in your environment variables
# or replace os.getenv("SERP_API_KEY") with your actual string key for testing
SERP_API_KEY = os.getenv("SERP_API_KEY") 

def get_logo(store):
    if not store:
        return "default.png"
    s = store.lower()
    if "amazon" in s:
        return "amazon.png"
    if "flipkart" in s:
        return "flipkart.png"
    if "reliance" in s:
        return "reliance.png"
    return "default.png"

def extract_price(p):
    if not p:
        return 0
    try:
        # Remove currency symbols, commas, and spaces
        clean_price = p.replace("₹", "").replace(",", "").strip()
        # Handle cases where price might be a range or contain text
        return int(float(clean_price.split()[0])) 
    except:
        return 0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    product = request.form.get("product")
    sort_order = request.form.get("sort")

    params = {
        "engine": "google_shopping",
        "q": product,
        "hl": "en",
        "gl": "in",
        "api_key": SERP_API_KEY
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return render_template("index.html", error="Failed to fetch results")

    results = []
    
    # Check if 'shopping_results' exists to avoid crashes
    shopping_results = data.get("shopping_results", [])

    for item in shopping_results:
        store = item.get("source", "Unknown")
        price = item.get("price", "N/A")
        
        # --- FIX STARTS HERE ---
        link = item.get("link")
        
        # 1. Fallback: Sometimes the main link is missing, try 'product_link'
        if not link:
            link = item.get("product_link")

        # 2. Fix Relative Links: If link starts with '/', it's a Google relative path
        if link and link.startswith("/"):
            link = f"https://www.google.co.in{link}"
        # --- FIX ENDS HERE ---

        results.append({
            "title": item.get("title"),
            "store": store,
            "price": price,
            "price_value": extract_price(price),
            "link": link,
            "logo": get_logo(store)
        })

    # Sort
    results.sort(
        key=lambda x: x["price_value"],
        reverse=(sort_order == "high")
    )

    return render_template("results.html", product=product, results=results)

if __name__ == "__main__":
    app.run(debug=True)