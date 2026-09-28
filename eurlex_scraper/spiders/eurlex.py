import json
from datetime import datetime, timedelta
import scrapy
from eurlex_scraper.storage import save_pdf


class EurLexSpider(scrapy.Spider):
    name = "eurlex"

    def __init__(self, target_date=None, sparql_url=None, language="ENG", *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not target_date:
            raise ValueError("target_date is required")

        if not sparql_url:
            raise ValueError("sparql_url is required")

        try:
            date_object = datetime.strptime(target_date, "%Y-%m-%d")

        except ValueError:
            raise ValueError("target_date must use YYYY-MM-DD format")

        self.target_date = target_date
        self.next_date = (date_object + timedelta(days=1)).strftime("%Y-%m-%d")
        self.sparql_url = sparql_url
        self.language = language.upper()
        self.seen_works = set()
        self.seen_items = set()
        self.scanned = 0
        self.downloaded = 0
        self.duplicates = 0
        self.skipped = 0
        self.failures = 0

    async def start(self):

        query = self.build_query()
        yield scrapy.Request(
            url=self.sparql_url,
            method="POST",
            body=query.encode("utf-8"),
            callback=self.parse_documents,
            errback=self.handle_failure,
            headers={
                "Content-Type": "application/sparql-query",
                "Accept": "application/sparql-results+json"
            }
        )

    def build_query(self):

        return f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX purl: <http://purl.org/dc/elements/1.1/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT
    ?work
    ?date
    ?legal_type
    ?celex
    ?title
    ?item

WHERE {{

    ?work rdf:type cdm:resource_legal .

    ?work cdm:work_date_document ?date .

    ?work cdm:work_created_by_agent
        <http://publications.europa.eu/resource/authority/corporate-body/ECB> .

    ?expression
        cdm:expression_belongs_to_work ?work ;
        cdm:expression_uses_language ?language .

    ?language
        purl:identifier ?langCode .

    FILTER (
        UCASE(STR(?langCode)) = "{self.language}"
    )

    ?manifestation
        cdm:manifestation_manifests_expression ?expression ;
        cdm:manifestation_type ?format .

    FILTER (
        LCASE(STR(?format)) = "pdf"
    )

    ?item
        cdm:item_belongs_to_manifestation ?manifestation .

    OPTIONAL {{
        ?work cdm:resource_legal_type ?legal_type .
    }}

    OPTIONAL {{
        ?work owl:sameAs ?celex .

        FILTER (
            CONTAINS(
                STR(?celex),
                "/resource/celex/"
            )
        )

    }}
    OPTIONAL {{

        ?expression
            cdm:expression_title ?title .

    }}
    FILTER (
        ?date >= "{self.target_date}"^^xsd:date
        &&
        ?date < "{self.next_date}"^^xsd:date
    )
}}
ORDER BY ?date
LIMIT 1000
"""
    def parse_documents(self, response):

        try:
            data = json.loads(response.text)
            results = data["results"]["bindings"]
        except (json.JSONDecodeError, KeyError):
            self.failures += 1
            self.logger.error("Could not read SPARQL response")
            return

        self.logger.info(
            "Query returned %s PDF rows",
            len(results)
        )

        for document in results:
            work_url = document.get("work", {}).get("value")

            item_url = document.get("item", {}).get("value")

            if not work_url or not item_url:
                self.skipped += 1
                continue


            if work_url not in self.seen_works:
                self.seen_works.add(work_url)
                self.scanned += 1

            if item_url in self.seen_items:
                continue

            self.seen_items.add(item_url)
            title = document.get("title", {}).get("value", "document")
            date = document.get("date", {}).get("value", self.target_date)

            celex = document.get("celex", {}).get("value")
            legal_type = document.get("legal_type", {}).get( "value")

            self.logger.info("FOUND PDF: %s", title)

            yield scrapy.Request(
                url=item_url,
                callback=self.parse_pdf,
                errback=self.handle_failure,
                headers={
                    "Accept": "application/pdf"
                },
                meta={
                    "title": title,
                    "date": date,
                    "celex": celex,
                    "legal_type": legal_type,
                    "work_url": work_url,
                    "item_url": item_url
                }
            )


    def parse_pdf(self, response):
        title = response.meta["title"]
        date = response.meta["date"]
        celex = response.meta["celex"]
        work_url = response.meta["work_url"]
        content_type = response.headers.get(
            "Content-Type",
            b""
        ).decode(
            "utf-8",
            errors="ignore"
        )
        if not response.body.startswith(b"%PDF"):
            self.skipped += 1
            self.logger.warning(
                "SKIPPED: Not a PDF | %s | %s",
                title,
                content_type
            )
            return
    
        result = save_pdf(
            content=response.body,
            title=title,
            work_url=work_url,
            date=date,
            celex=celex
        )
        if result == "downloaded":
            self.downloaded += 1

        elif result == "duplicate":
            self.duplicates += 1


    def handle_failure(self, failure):
        self.failures += 1
        response = getattr(
            failure.value,
            "response",
            None
        )
        if response:
            status = response.status

        else:
            status = "NO RESPONSE"

        self.logger.error(
            "REQUEST FAILED [%s]: %s | %s",
            status,
            failure.request.url,
            failure.value
        )

    def closed(self, reason):
        print("\n========== RUN SUMMARY ==========")
        print("TARGET DATE:", self.target_date)
        print("DOCUMENTS SCANNED:", self.scanned)
        print("DOWNLOADED:", self.downloaded)
        print("DUPLICATES:", self.duplicates)
        print("SKIPPED:", self.skipped)
        print("FAILURES:", self.failures)
        print("=================================")