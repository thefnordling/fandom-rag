import json
import time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import argparse
from urllib.parse import quote

SLEEP_BETWEEN_REQUESTS = 0.5
RETRY_DELAY = 5
MAX_RETRIES = 3


def get_all_article_titles(page):
    titles = []
    apcontinue = None
    print("🔍 Collecting article titles using API in browser context...")

    while True:
        url = f"{API_URL}?action=query&list=allpages&aplimit=max&format=json"
        if apcontinue:
            url += f"&apcontinue={apcontinue}"

        page.goto(url)
        content = page.locator("body").text_content()
        try:
            data = json.loads(content)
        except Exception as e:
            print(f"❌ Failed to parse JSON from API: {e}")
            print(content[:500])
            break

        pages = data.get("query", {}).get("allpages", [])
        titles.extend(page["title"] for page in pages)

        apcontinue = data.get("continue", {}).get("apcontinue")
        if not apcontinue:
            break

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    print(f"✅ Found {len(titles)} articles.")
    return titles


def fetch_article_content(page, title):
    for attempt in range(1, MAX_RETRIES + 1):
        encoded_title = quote(title, safe="")
        url = f"{API_URL}?action=parse&page={encoded_title}&format=json&prop=text&formatversion=2"
        try:
            page.goto(url)
            content = page.locator("body").text_content()
            data = json.loads(content)
            html = data.get("parse", {}).get("text", "")
            if html:
                return {
                    "title": title,
                    "url": f"{BASE_URL}/wiki/{encoded_title}",
                    "html": html
                }
        except Exception as e:
            print(f"❌ Attempt {attempt} failed for {title}: {e}")
            time.sleep(RETRY_DELAY)

    return None


def fetch_article_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def main(wiki_name, output_file):
    global BASE_URL, API_URL
    BASE_URL = f"https://{wiki_name}.fandom.com"
    API_URL = f"{BASE_URL}/api.php"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        titles = get_all_article_titles(page)

        print(f"\n🚀 Fetching {len(titles)} pages serially...\n")

        with open(output_file, "w", encoding="utf-8") as f:
            for i, title in enumerate(titles, 1):
                result = fetch_article_content(page, title)
                if result:
                    result["text"] = fetch_article_text_from_html(result["html"])
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                else:
                    print(f"⚠️ Skipped: {title}")
                print(f"Progress: {i}/{len(titles)}", end="\r")
                time.sleep(SLEEP_BETWEEN_REQUESTS)

        browser.close()
        print(f"\n🎉 Done! Scraped articles written to {output_file}")

if __name__ == "__main__":
    # Remove output file if it exists from previous runs
    parser = argparse.ArgumentParser(description="Scrape a Fandom wiki by name.")
    parser.add_argument("wiki_name", help="The subdomain name of the fandom wiki (e.g. 'pokemon' for pokemon.fandom.com)")
    args = parser.parse_args()
    output_file = f"{args.wiki_name}.jsonl"
    Path(output_file).unlink(missing_ok=True)
    main(args.wiki_name, output_file)
