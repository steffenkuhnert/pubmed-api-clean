from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from xml.etree import ElementTree

app = Flask(__name__)
CORS(app)

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
    keyword = data.get("keyword")

    if not keyword:
        return jsonify({"error": "Missing 'keyword' parameter"}), 400

    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": keyword,
        "sort": "pub+date",
        "retmax": 5,
        "retmode": "json"
    }
    search_response = requests.get(search_url, params=params).json()
    ids = search_response["esearchresult"]["idlist"]

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
        title = article.findtext(".//ArticleTitle")
        abstract = article.findtext(".//AbstractText")
        pmid = article.findtext(".//PMID")
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        articles.append({
            "title": title,
            "abstract": abstract,
            "link": link
        })

    return jsonify({"results": articles})