# EUR-Lex PDF Scraper

This project is a Python scraper that finds and downloads ECB legal documents for a specific date.
The user provides a date when running the scraper. The scraper then searches the EU CELLAR document system for ECB legal documents matching that date and downloads the available English PDF files.
The scraper also keeps track of downloaded files so the same PDF is not downloaded more than once.

## Main Features
- Accepts a date from the user at runtime
- Searches for ECB legal documents
- Filters documents by date
- Filters for English documents
- Downloads PDF files
- Checks that the downloaded file is a real PDF
- Prevents duplicate downloads
- Stores information about downloaded files in a manifest
- Displays a summary at the end of every run
- Handles failed requests and invalid input

## Open-Source Library Used
The main open-source scraping library used in this project is: Scrapy
Scrapy is used to:
- send HTTP requests
- receive responses
- download PDF files
- handle request failures
- control crawling speed
- log scraper activity
Version used: Scrapy 2.19.0

## Why CELLAR Is Used
The original task was based on EUR-Lex search results.
During development, direct automated access to the EUR-Lex frontend was not reliable because the site returned JavaScript and anti-bot challenge pages.
For this reason, the scraper uses the official EU CELLAR data service instead.
CELLAR is the EU document repository used to store and expose EU publication metadata and files.
The scraper sends a SPARQL query to CELLAR to find matching documents and their PDF files.
The SPARQL endpoint used is: https://publications.europa.eu/webapi/rdf/sparql

## How the Scraper Works
The basic flow is:
1. User enters a date
2. Scrapy starts the spider
3. A SPARQL query is created
4. CELLAR searches for matching ECB legal documents
5. English PDF items are found
6. Scrapy downloads the PDF
7. The file hash is checked
8. New PDF => save it
9. Duplicate => skip it

### Important Files

`eurlex.py`
Contains the main scraper logic.
- receives the target date
- builds the SPARQL query
- finds matching documents
- finds PDF item URLs
- downloads PDFs
- tracks run statistics

`storage.py`
Handles file storage and duplicate detection.
- creates the download folder
- calculates a SHA-256 hash for each PDF
- checks the manifest for duplicates
- saves new PDFs
- updates `manifest.json`

`settings.py`
Contains Scrapy settings such as request delay and concurrency.

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/mariiejjose/scraper.git
```

Move into the project folder:
```powershell
cd scraper
```

### 2. Create a virtual environment

```powershell
py -m venv venv
```

Activate it:
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install the required packages

```powershell
pip install -r requirements.txt
```

## How to Run the Scraper

The scraper requires:
- a target date
- the CELLAR SPARQL endpoint

The date must use this format: YYYY-MM-DD

Run the scraper with:
scrapy crawl eurlex -a target_date=YYYY-MM-DD -a "sparql_url=https://publications.europa.eu/webapi/rdf/sparql"

## Date Meaning

The current scraper uses the CELLAR field: work_date_document
Therefore, `target_date` currently means the document date.
It does not necessarily mean the date the document was published in the Official Journal.

## Language Configuration

The default language is English:
The language can also be supplied as a spider argument.
scrapy crawl eurlex -a target_date=2026-09-01 -a language=ENG -a "sparql_url=https://publications.europa.eu/webapi/rdf/sparql"

## Duplicate Detection

Every downloaded PDF is given a SHA-256 hash.
The hash works like a fingerprint for the file.
When a PDF is found:
1. Calculate PDF hash
2. Check manifest.json
3. Hash already exists?
    a. Yes => Duplicate
    b. No => Save PDF

This prevents the same PDF from being downloaded again, even across different scraper runs.
Downloaded file information is stored in: manifest.json

## Downloaded Files

Normal downloaded PDFs are saved inside: downloads/
The `downloads` folder and `manifest.json` are ignored by Git because they are runtime files.
A separate `sample_output` folder is included in the repository to show the result of one real sample run.

## Run Summary
At the end of a run, the scraper displays a summary similar to:
========== RUN SUMMARY ==========
TARGET DATE: 2026-09-01
DOCUMENTS SCANNED: 1
DOWNLOADED: 0
DUPLICATES: 1
SKIPPED: 0
FAILURES: 0
=================================

### Meaning of the Counters

`DOCUMENTS SCANNED`: Number of unique legal documents found.
`DOWNLOADED`: Number of new PDFs saved.
`DUPLICATES`: Number of PDFs already found in the manifest.
`SKIPPED`: Results that could not be processed, for example because required information was missing or the returned content was not a PDF.
`FAILURES`: Requests that failed.

## Scraping Configuration

The project uses responsible request settings.
Important settings include:
```python
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 10
DOWNLOAD_DELAY_JITTER = 0
```
These settings reduce the number of requests sent at the same time and add a delay between requests.

## Known Limitation

The original assignment describes navigating EUR-Lex search-result pages.
During development, direct automated access to the EUR-Lex frontend was blocked or made unreliable by its web protection system.
The final implementation therefore uses the official CELLAR machine-readable data service for document discovery and PDF retrieval.
Because the SPARQL query directly filters the requested date, the scraper does not need to navigate through older frontend search-result pages.

## Repository
GitHub repository: https://github.com/mariiejjose/scraper
