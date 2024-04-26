import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import sqlite3
import concurrent.futures
from typing import List, Tuple, Optional
import time
import logging

TOC_JSON = "https://learn.microsoft.com/en-us/azure/templates/toc.json"
URL_PREFIX = "https://learn.microsoft.com/en-us/azure/templates/"
BOOTSTRAP_CSS = "./bootstrap.min.css"
RESOURCE_LINK = "https://learn.microsoft.com"
NUMBER_OF_THREADS = 50
REFERENCE_INDEX = 2
logging.basicConfig(level=logging.INFO)

index = {
    "resource-format-1": "Resource Format",
    "property-values-1": "Property Values",
    "quickstart-templates": "Quickstart Templates",
    "arm-template-resource-definition": "ARM Template Resource Definition",
}


def process_toc_json(obj, links=None):
    if links is None:
        links = []

    if isinstance(obj, dict):
        if obj["toc_title"] != "(API versions)":
            for k, v in obj.items():
                if k == "children":
                    process_toc_json(v, links)
                if k == "href":
                    links.append(v)

    elif isinstance(obj, list):
        for i in obj:
            process_toc_json(i, links)

    return links


def populate_db(records):
    q = "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?, ?, ?)"
    values = []
    for record in records:
        name, type, path = record
        name = name.replace("'", "")
        values.append((name, type, path))

    conn = sqlite3.connect("docSet.dsidx")
    c = conn.cursor()
    c.executemany(q, values)
    conn.commit()
    conn.close()


def extract_links(json_toc, folder_name="downloaded_pages"):
    response = requests.get(json_toc)
    if response.status_code != 200:
        raise Exception("Failed to fetch the TOC JSON")

    json_doc = response.json()
    items = json_doc.get("items", [{}])
    if len(items) <= REFERENCE_INDEX:
        raise Exception("No Reference item found in json document")

    reference_item = items[REFERENCE_INDEX]
    if reference_item.get("toc_title") != "Reference":
        raise Exception("No reference item found in json document")

    resources = reference_item.get("children", [])
    if not resources:
        raise Exception("No resources found")

    logging.info(f"Found {len(resources)} resources")
    logging.info("Extracting link of resources...")
    links = process_toc_json(resources)
    logging.info(f"Number of found links: {len(links)}")
    return links


def download_with_threads(
    links: List[str], folder_name: str = "./downloaded_pages"
) -> List[Tuple[str, str, str]]:
    """
    Downloads multiple web pages concurrently using threads.

    Args:
        links (List[str]): A list of URLs of the web pages to download.
        folder_name (str, optional): The name of the folder where the downloaded pages will be saved.
            Defaults to "./downloaded_pages".

    Returns:
        List[Tuple[str, str, str]]: A list of tuples containing information about the downloaded pages.
            Each tuple contains the URL, file name, and status of the downloaded page.

    Raises:
        Exception: If there is an error while downloading a page.

    """
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    records = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=NUMBER_OF_THREADS
    ) as executor:
        futures = [
            executor.submit(download_single_page, link, folder_name) for link in links
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                records.append(result)
            except Exception as e:
                logging(f"Failed to download a page: {e}")

    return records


def download_single_page(link: str, folder_name: str) -> None:
    link = urljoin(URL_PREFIX, link)
    html = create_empty_html(link)
    downloaded_html = fetch_page(link)
    new_html = BeautifulSoup(html, "html.parser")
    resource_title = move_header(downloaded_html, new_html)
    move_deployment_template(downloaded_html, new_html)
    add_table_class(new_html)
    add_anchor_tags(new_html)
    add_pre_class(new_html)
    add_resource_link(new_html)
    replace_relative_paths(new_html, link)
    replace_src_image(new_html)
    file_name = save_html_file(new_html, link, folder_name)
    return (resource_title, "Resource", file_name)


def create_empty_html(link: str) -> str:
    return f"""
    <html>
        <!-- Online page at {link} -->
        <head>
            <link href="{BOOTSTRAP_CSS}" rel="stylesheet">
        </head>
        <body class="container">
        </body>
    </html>
    """


def fetch_page(link: str) -> BeautifulSoup:
    response = requests.get(link)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch the page {link}")
    return BeautifulSoup(response.text, "html.parser")


def move_header(downloaded_html: BeautifulSoup, new_html: BeautifulSoup) -> None:
    header = downloaded_html.find("h1")
    if header is None:
        raise Exception("No header found")
    header.text.replace("'", "")
    new_html.body.append(header)
    return header.text


def move_deployment_template(
    downloaded_html: BeautifulSoup, new_html: BeautifulSoup
) -> None:
    arm = downloaded_html.find(
        "div", {"data-pivot": "deployment-language-arm-template"}
    )
    if arm is None:
        raise Exception("No Deployment Template found")
    new_html.body.append(arm)


def add_table_class(new_html: BeautifulSoup) -> None:
    for table in new_html.find_all("table"):
        table["class"] = "table"


def add_anchor_tags(new_html: BeautifulSoup) -> None:
    for h2 in new_html.find_all("h2"):
        if h2.get("id") in [
            "resource-format-1",
            "property-values-1",
            "quickstart-templates",
            "arm-template-resource-definition",
        ]:
            a = new_html.new_tag("a")
            a["class"] = "dashAnchor"
            a["name"] = f"//apple_ref/cpp/Section/{index[h2.get('id')]}"
            h2.insert_before(a)


def add_pre_class(new_html: BeautifulSoup) -> None:
    for pre in new_html.find_all("pre"):
        pre["class"] = "text-bg-light"


def add_resource_link(new_html: BeautifulSoup) -> None:
    for a in new_html.find_all("a", {"data-linktype": "absolute-path"}):
        a["href"] = RESOURCE_LINK + a["href"]


def replace_relative_paths(new_html: BeautifulSoup, link: str) -> None:
    for a in new_html.find_all("a", {"data-linktype": "relative-path"}):
        a["href"] = link


def replace_src_image(new_html: BeautifulSoup) -> None:
    for img in new_html.find_all(
        "img", {"data-linktype": "relative-path", "alt": "Deploy to Azure"}
    ):
        img["src"] = "./index_files/deploy-to-azure.svg"


def save_html_file(new_html: BeautifulSoup, link: str, folder_name: str) -> None:
    file_name = (
        os.path.join(folder_name, os.path.basename(urlparse(link).path)) + ".html"
    )
    with open(file_name, "w") as f:
        f.write(str(new_html))
    logging.info(f"Page saved in {file_name}")
    return os.path.basename(urlparse(link).path) + ".html"


def create_db(db_file: Optional[str] = "docSet.dsidx") -> None:
    if os.path.exists(db_file):
        os.remove(db_file)

    try:
        with sqlite3.connect(db_file) as conn:
            c = conn.cursor()
            c.execute(
                "CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
            )
            c.execute("CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);")
    except sqlite3.Error as e:
        logging.error(f"An error occurred: {e}")


if __name__ == "__main__":
    start_time = time.time()
    create_db()
    logging.info("Extracting ARM resources...")
    links = extract_links(TOC_JSON)
    logging.info("Downloading pages...")
    records = download_with_threads(links, "./downloaded_pages")
    logging.info("Inserting records in database...")
    populate_db(records)
    end_time = time.time()
    logging.info(f"Time taken: {end_time - start_time:.2f} seconds")
