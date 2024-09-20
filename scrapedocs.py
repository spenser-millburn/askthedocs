import typer
import os
import requests
from bs4 import BeautifulSoup
import pdfplumber
import pdfkit
from PyPDF2 import PdfMerger
import logging
import pandas as pd

# Configure logging
logging.basicConfig(filename='cli_errors.log', level=logging.ERROR)

app = typer.Typer()

# Step 1: Scrape the Table of Contents
def scrape_toc(url: str, output_csv: str):
    """Scrapes the Table of Contents from a given documentation URL."""
    response = requests.get(url)
    if response.status_code != 200:
        typer.echo(f"Failed to retrieve page with status code {response.status_code}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    toc_section = soup.find('div', {'class': 'toctree-wrapper'})
    
    if not toc_section:
        typer.echo("Failed to locate the Table of Contents section")
        return
    
    toc_items = toc_section.find_all('a', href=True)
    contents = []
    for item in toc_items:
        content_text = item.get_text()
        content_link = item['href']
        if content_link.startswith("/"):
            content_link = f"{url.rstrip('/')}{content_link}"
        contents.append({'Title': content_text, 'Link': content_link})

    df = pd.DataFrame(contents)
    df.to_csv(output_csv, index=False)
    typer.echo(f"Scraped TOC and saved to {output_csv}")

# Step 2: Save HTML files
def save_html_from_toc(csv_file: str, output_dir: str, url:str):
    """Save HTML files for each TOC entry."""
    df = pd.read_csv(csv_file)
    os.makedirs(output_dir, exist_ok=True)
    
    for _, row in df.iterrows():
        title = row['Title']
        link = row['Link']
        response = requests.get(url+"/"+link)
        if response.status_code == 200:
            filename = f"{title.replace(' ', '_')}.html"
            file_path = os.path.join(output_dir, filename)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                typer.echo(f"Saved {file_path}")
            except Exception as e:
                print(f"Exception in writing file during save_html_from_toc. { file_path} : {e}")
        else:
            typer.echo(f"Failed to retrieve {link} (status code: {response.status_code})")

# Step 3: Convert HTML to PDF
def convert_html_to_pdf(folder_path: str):
    """Convert HTML files in a folder to PDFs."""
    output_folder = os.path.join(folder_path, 'pdf_output')
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(folder_path):
        if filename.endswith('.html'):
            html_file = os.path.join(folder_path, filename)
            pdf_file = os.path.join(output_folder, f'{os.path.splitext(filename)[0]}.pdf')

            try:
                pdfkit.from_file(html_file, pdf_file)
                typer.echo(f"Successfully converted: {filename} to PDF")
            except Exception as e:
                logging.error(f"Failed to convert {filename}: {str(e)}")
                typer.echo(f"Error converting {filename}. Check log for details.")

# Step 4: Concatenate PDFs
def concatenate_pdfs(folder_path: str, output_pdf: str):
    """Concatenate all PDFs in the folder into a single PDF."""
    merger = PdfMerger()
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            pdf_file = os.path.join(folder_path, filename)
            try:
                merger.append(pdf_file)
                typer.echo(f"Added {filename} to merge")
            except Exception as e:
                typer.echo(f"Error adding {filename}: {str(e)}")

    try:
        with open(output_pdf, 'wb') as f:
            merger.write(f)
        typer.echo(f"Successfully created merged PDF: {output_pdf}")
    except Exception as e:
        typer.echo(f"Error saving the merged PDF: {str(e)}")
    finally:
        merger.close()

# Step 5: Convert PDF to Markdown
def pdf_to_markdown(pdf_path: str, output_md: str):
    """Convert a PDF file to a Markdown file."""
    with pdfplumber.open(pdf_path) as pdf:
        markdown_text = ""
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                markdown_text += f"# Page {page_num}\n\n{text}\n\n"
            else:
                typer.echo(f"No text found on page {page_num}")
        
        with open(output_md, 'w', encoding='utf-8') as md_file:
            md_file.write(markdown_text)
        
        typer.echo(f"Successfully converted {pdf_path} to Markdown at {output_md}")

# Typer Commands
@app.command()
def scrape_and_save(url: str, output_csv: str, output_dir: str):
    """Scrape TOC from a URL and save as HTML files."""
    scrape_toc(url, output_csv)
    save_html_from_toc(output_csv, output_dir, url)

@app.command()
def convert_and_concatenate(output_dir: str, output_pdf: str):
    """Convert HTML files to PDF and concatenate them."""
    convert_html_to_pdf(output_dir)
    concatenate_pdfs(os.path.join(output_dir, 'pdf_output'), output_pdf)

@app.command()
def pdf_to_md(input_pdf: str, output_md: str):
    """Convert a PDF to Markdown."""
    pdf_to_markdown(input_pdf, output_md)

if __name__ == "__main__":
    app()
