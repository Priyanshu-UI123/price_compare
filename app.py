from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

SERP_API_KEY = "d66eccb121b3453152187f2442537b0fe5b3c82c4b8d4d56b89ed4d52c9f01a6"


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    product = request.form.get("product")
    sort_order = request.form.get("sort", "high")

    # Image upload (optional)
    if "image" in request.files and request.files["image"].filename != "":
        image = request.files["image"]
        product = image.filename.rsplit(".", 1)[0]  # simple fallback name

    params = {
        "engine": "google_shopping",
        "q": product,
        "hl": "en",
        "gl": "in",
        "api_key": SERP_API_KEY
    }

    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()

    results = []

    for item in data.get("shopping_results", []):
        price = item.get("price")
        link = (
            item.get("shopping_link")
            or item.get("product_link")
            or item.get("offers_link")
        )

        if price:
            store = item.get("source", "Store")

            results.append({
                "title": item.get("title"),
                "store": store,
                "logo": get_logo(store),
                "price": price,
                "link": link
            })

    def price_num(p):
        try:
            return float(p.replace("₹", "").replace(",", ""))
        except:
            return 0

    results.sort(
        key=lambda x: price_num(x["price"]),
        reverse=(sort_order == "high")
    )

    return render_template(
        "results.html",
        product=product,
        results=results,
        sort_order=sort_order
    )


def get_logo(store):
    store = store.lower()
    if "amazon" in store:
        return "amazon.png"
    if "flipkart" in store:
        return "flipkart.png"
    if "croma" in store:
        return "croma.png"
    return "default.png"


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

