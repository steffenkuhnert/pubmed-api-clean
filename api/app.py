from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from xml.etree import ElementTree

app = Flask(__name__)
CORS(app)

# Einfache Synonym- und Übersetzungstabellen
synonym_map = {
    "l-theanin": "l-theanine",
    "schlafstörung": "sleep disorder",
    "schlafstörungen": "sleep disorders",
    "angststörung": "anxiety disorder",
    "depression": "depression",
    "bluthochdruck": "hypertension"
}

def normalize_keyword(keyword):
    keyword = keyword.strip().lower()
    return synonym_map.get(keyword, keyword)

@app.route("/", methods=["GET"])
def tool_definitions():
    return jsonify([
        {
            "name": "PubMed Search",
            "description": "Suche nach aktuellen Studien auf PubMed zu einem Schlagwort",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Begriff, nach dem in PubMed gesucht werden soll"
                    }
                },
                "required": ["keyword"]
            }
        }
    ])

@app.route("/pubmed-search", methods=["POST"])
def pubmed_search():
    data = request.json
    keyword = data.get("keyword", "").strip()
    
    if not keyword:
        return jsonify({"error": "Missing 'keyword' parameter"}), 400

    normalized_keyword = normalize_keyword(keyword)

    # 1. Suche nach PubMed IDs
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": normalized_keyword,
        "sort": "pub+date",
        "retmax": 10,
        "retmode": "json"
    }
    search_response = requests.get(search_url, params=params).json()
    ids = search_response["esearchresult"]["idlist"]

    if not ids:
        return jsonify({"results": []})

    # 2. Details abrufen
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml"
    }
    fetch_response = requests.get(fetch_url, params=fetch_params)
    tree = ElementTree.fromstring(fetch_response.content)
    articles = []

    for article in tree.findall(".//PubmedArticle"):
        title = article.findtext(".//ArticleTitle") or "Kein Titel verfügbar"
        abstract = article.findtext(".//AbstractText") or "Kein Abstract verfügbar"
        pmid = article.findtext(".//PMID")
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        # Studienart erkennen (falls vorhanden)
        publication_types = [pt.text for pt in article.findall(".//PublicationType") if pt.text]
        study_type = ", ".join(publication_types)

        articles.append({
            "title": title,
            "abstract": abstract,
            "link": link,
            "type": study_type
        })

    # 3. Sortierung: Meta-Analyse > RCT > andere
    def sort_key(article):
        t = article["type"].lower()
        if "meta-analysis" in t:
            return 0
        elif "randomized controlled trial" in t or "randomised controlled trial" in t:
            return 1
        else:
            return 2

    sorted_articles = sorted(articles, key=sort_key)

    return jsonify({"results": sorted_articles})