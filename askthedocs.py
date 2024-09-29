import requests
from bs4 import BeautifulSoup
import typer
import os
from urllib.parse import urljoin, urlparse

# Define the CLI app using Typer
app = typer.Typer()

# Function to recursively find and print all pages from a base URL with depth tracking
def find_all_pages(base_url: str, url: str, maxdepth: int, current_depth: int = 0, keyword: str = "", links: set = None):
    if links is None:
        links = set()

    # Stop recursion if maxdepth is reached
    if current_depth > maxdepth:
        return links

    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure we got a successful response

        soup = BeautifulSoup(response.content, 'html.parser')

        # Process all <a> tags with valid hrefs
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            # Convert relative links to absolute URLs
            full_link = urljoin(base_url, link)

            # Parse the URL to filter out external links
            parsed_base_url = urlparse(base_url)
            parsed_link = urlparse(full_link)

            # Ensure the link is within the same domain and not an external site
            if parsed_base_url.netloc != parsed_link.netloc:
                continue

            # Ensure the link has not been visited and contains the keyword if specified
            if keyword in full_link and full_link not in links:
                links.add(full_link)
                print(f'Found: {full_link}')
                # Recursively find more pages, increasing the depth
                find_all_pages(base_url, full_link, maxdepth, current_depth + 1, keyword, links)

    except requests.exceptions.RequestException as e:
        print(f'Error fetching {url}: {e}')

    return links

# Function to save page content as a text file
def save_page_as_text(url: str, pdf_dir: str):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure we got a successful response

        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = soup.get_text()

        # Create the directory if it doesn't exist
        os.makedirs(pdf_dir, exist_ok=True)

        # Sanitize the URL to create a valid file name
        file_name = os.path.join(pdf_dir, f"{url.replace('https://', '').replace('http://', '').replace('/', '_')}.txt")
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(page_text)

        print(f'Saved {url} as {file_name}')

    except requests.exceptions.RequestException as e:
        print(f'Error saving {url}: {e}')

# Main function that integrates the functionalities and provides CLI options
@app.command()
def main(
    url: str = "https://docs.prefect.io/",
    maxdepth: int = 2,
    output_dir: str = "./output",
    keyword: str = "",
    print_links_only: bool = False
):
    links = find_all_pages(url, url, maxdepth, current_depth=0, keyword=keyword)

    if print_links_only:
        for link in links:
            print(link)
    else:
        for link in links:
            save_page_as_text(link, output_dir)

if __name__ == "__main__":
    app()
