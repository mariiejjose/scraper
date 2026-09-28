import requests
from datetime import datetime, timedelta
from eurlex_scraper.storage import save_pdf

target_date = "2025-09-18"
date_object = datetime.strptime(target_date, "%Y-%m-%d")
next_date = date_object + timedelta(days=1)
next_date_string = next_date.strftime("%Y-%m-%d")
url = "https://publications.europa.eu/webapi/rdf/sparql"


query = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT
    ?work
    ?date
    ?legal_type
    ?celex
    ?title

WHERE {{
    ?work rdf:type cdm:resource_legal .

    ?work cdm:work_date_document ?date .

    ?work cdm:work_created_by_agent
        <http://publications.europa.eu/resource/authority/corporate-body/ECB> .

    OPTIONAL {{
        ?work cdm:resource_legal_type ?legal_type .
    }}
    OPTIONAL {{
        ?work owl:sameAs ?celex .

        FILTER(
            CONTAINS(
                STR(?celex),
                "/resource/celex/"
            )
        )
    }}
    OPTIONAL {{
        ?expression
            cdm:expression_belongs_to_work ?work ;
            cdm:expression_uses_language
                <http://publications.europa.eu/resource/authority/language/ENG> ;
            cdm:expression_title ?title .
    }}
    FILTER (
        ?date >= "{target_date}"^^xsd:date
        &&
        ?date < "{next_date_string}"^^xsd:date
    )
}}
ORDER BY ?date
LIMIT 100
"""

response = requests.get(
    url,
    params={
        "query": query,
        "format": "application/sparql-results+json"
    },
    timeout=30
)
print("STATUS:", response.status_code)

data = response.json()
results = data["results"]["bindings"]

if results:
    first_document = results[0]

    work_url = first_document["work"]["value"]

    print("\nTESTING PDF DOWNLOAD")
    print("WORK:", work_url)

    pdf_response = requests.get(
        work_url,
        headers={
            "Accept": "application/pdf",
            "Accept-Language": "eng"
        },
        allow_redirects=True,
        timeout=60
    )

    print("PDF STATUS:", pdf_response.status_code)
    print("CONTENT TYPE:", pdf_response.headers.get("Content-Type"))
    print("SIZE:", len(pdf_response.content), "bytes")
    print("FIRST BYTES:", pdf_response.content[:4])

    if (
    pdf_response.status_code == 200
    and pdf_response.content.startswith(b"%PDF")
    ):
        title = first_document.get("title", {}).get("value", "document")
        date = first_document.get("date", {}).get("value")
        celex = first_document.get("celex", {}).get("value")

        save_pdf(
            content=pdf_response.content,
            title=title,
            work_url=work_url,
            date=date,
            celex=celex
        )
print("LEGAL DOCUMENTS FOUND:", len(results))

for document in results:

    print("\n-----------------------------")
    print("WORK:", document.get("work", {}).get("value"))
    print("DATE:", document.get("date", {}).get("value"))
    print("LEGAL TYPE:", document.get("legal_type", {}).get("value"))
    print("CELEX:", document.get("celex", {}).get("value"))
    print("TITLE:", document.get("title", {}).get("value"))