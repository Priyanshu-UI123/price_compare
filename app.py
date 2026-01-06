from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

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
        clean_price = p.replace("₹", "").replace(",", "").strip()
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
        print(f"Error: {e}")
        return render_template("index.html", error="Error fetching results")

    results = []
    for item in data.get("shopping_results", []):
        store = item.get("source", "Unknown")
        price = item.get("price", "N/A")
        link = item.get("link") or item.get("product_link") # Fallback
        
        # Link fix
        if link and link.startswith("/"):
            link = f"https://www.google.co.in{link}"

        results.append({
            "title": item.get("title"),
            "store": store,
            "price": price,
            "price_value": extract_price(price),
            "link": link,
            "thumbnail": item.get("thumbnail"), # New: Get Image
            "logo": get_logo(store)
        })

    results.sort(
        key=lambda x: x["price_value"],
        reverse=(sort_order == "high")
    )

    return render_template("results.html", product=product, results=results)

if __name__ == "__main__":
    app.run(debug=True)