# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "bs4",
# ]
# ///



import argparse
import sys
import json
from bs4 import BeautifulSoup

def extract_links(html_file_path, link_text):
    """
    Reads an HTML file and extracts all links with a given text in the link text.

    :param html_file_path: Path to the HTML file.
    :param link_text: The text to search for in the link.
    """
    try:
        with open(html_file_path, 'r') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{html_file_path}' was not found.", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(html_content, 'html.parser')
    
    matching_links = []
    for a_tag in soup.find_all('a'):
        if link_text in a_tag.get_text():
            href = a_tag.get('href')
            if href:
                matching_links.append(json.dumps({ 'href': href, 'text': a_tag.get_text() }))
    
    return matching_links

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts all links from an HTML file that contain a specific text.')
    parser.add_argument('html_file', help='The HTML file to parse.')
    parser.add_argument('link_text', help='The text to search for in the link text.')
    
    args = parser.parse_args()
    
    links = extract_links(args.html_file, args.link_text)
    
    if links:
        print('\n'.join(links))


