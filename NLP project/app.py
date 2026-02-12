from flask import Flask, request, jsonify, render_template
import pandas as pd
import re
import json
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# LOAD DATASET

df = pd.read_csv("cleaned_dataset.csv")
df.columns = df.columns.str.strip()

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    return text

df["processed_text"] = df["menuItemName"].apply(clean_text)

vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(df["processed_text"])


# LOGGING FUNCTION (FOR EVALUATION)

def log_search(query, status, results):

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "status": status,
        "results": results
    }

    with open("search_logs.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")



# HOME ROUTE

@app.route("/")
def home():
    return render_template("front.html")



# SEARCH ROUTE

@app.route("/search", methods=["POST"])
def search():

    user_input = request.json.get("query", "")
    cleaned_input = clean_text(user_input)

    # Exact match
    exact_match = df[df["processed_text"] == cleaned_input]

    if not exact_match.empty:
        item = exact_match.iloc[0]

        log_search(user_input, "exact_match", [item["menuItemName"]])

        return jsonify({
            "status": "found",
            "item_name": item["menuItemName"],
            "description": item["menuItemDescription"],
            "price": item["menuItemCurrentPrice"],
            "category": item["menuItemCategory"],
            "image": item["menuItemImageUrl"],
            "restaurant": item["restaurantName"],
            "rating": round(float(item["menuItemAverageRating"]), 1)
        })

    # Cosine similarity fallback
    user_vector = vectorizer.transform([cleaned_input])
    similarities = cosine_similarity(user_vector, tfidf_matrix)
    similar_indices = similarities.argsort()[0][-3:][::-1]

    recommendations = df.iloc[similar_indices][[
        "menuItemName",
        "menuItemCurrentPrice",
        "menuItemImageUrl",
        "restaurantName"
    ]]

    result_names = recommendations["menuItemName"].tolist()

    log_search(user_input, "similarity_fallback", result_names)

    return jsonify({
        "status": "not_found",
        "message": "We don’t have that item, but you might like:",
        "recommendations": recommendations.to_dict(orient="records")
    })


if __name__ == "__main__":
    app.run(debug=True)
