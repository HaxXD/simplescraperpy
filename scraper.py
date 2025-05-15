import requests
from bs4 import BeautifulSoup
import time
import concurrent.futures
from tqdm import tqdm
import logging

# List of proxy list websites to scrape (you can add more)
PROXY_SITES = [
    'https://www.free-proxy-list.net',
    'https://www.socks-proxy.net',
    'https://www.us-proxy.org',
    'https://www.sslproxies.org',
    'https://www.freeproxylist.org/',
    'https://www.proxynova.com/proxy-server-list/',
    'https://www.spys.one/en/free-proxy-list/',
    'https://www.getproxylist.com',
    'https://www.undesired.com/proxies/'
]

# Valid protocols
VALID_PROTOCOLS = ['http', 'https', 'socks4', 'socks5']

# Retry settings
MAX_RETRIES = 3
BACKOFF_FACTOR = 2  # Exponential backoff factor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to print ASCII art header


# Function to scrape proxies from a website
def scrape_proxies(url):
    proxies = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    
    # Retry logic
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise HTTPError for bad responses
            if response.status_code == 200:
                if url.endswith('.json'):
                    # If the URL returns a JSON list of proxies
                    proxy_list = response.text.splitlines()
                    for proxy in proxy_list:
                        ip, port = proxy.split(':')
                        protocol = 'http'  # Default to HTTP
                        proxies.append((ip, port, protocol))
                else:
                    # Handle HTML pages as before
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for row in soup.find_all('tr'):
                        tds = row.find_all('td')
                        if len(tds) > 1:  # Ensure the row contains at least two <td> elements
                            ip = tds[0].get_text().strip()
                            port = tds[1].get_text().strip()
                            protocol = tds[6].get_text().strip() if len(tds) > 6 else 'http'
                            if protocol.lower() not in VALID_PROTOCOLS:
                                protocol = 'http'  # Default to 'http' if the protocol is invalid
                            if ip and port:
                                proxies.append((ip, port, protocol.lower()))
            return proxies
        except (requests.RequestException, ValueError) as e:
            logging.error(f"Error scraping {url}: {e}")
            retries += 1
            time.sleep(BACKOFF_FACTOR ** retries)  # Exponential backoff
    return proxies

# Function to check if a proxy is working and measure response time
def check_proxy(proxy, working_proxies):
    ip, port, protocol = proxy
    url = 'http://httpbin.org/ip'  # A simple endpoint to check if the proxy is working
    proxies = {protocol: f'{protocol}://{ip}:{port}'}
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, proxies=proxies, timeout=5)
            response.raise_for_status()
            if response.status_code == 200:
                logging.info(f'{ip}:{port} ({protocol}) is working')
                working_proxies[protocol].append(f'{ip}:{port}')
                save_proxies(working_proxies)  # Save immediately after check
            return
        except requests.RequestException as e:
            
            retries += 1
            time.sleep(BACKOFF_FACTOR ** retries)  # Exponential backoff

# Function to save proxies to the corresponding file
def save_proxies(proxies_by_protocol):
    for protocol, proxies in proxies_by_protocol.items():
        with open(f'{protocol}.txt', 'a') as file:
            for proxy in proxies:
                file.write(proxy + '\n')
        logging.info(f"Saved {len(proxies)} {protocol} proxies to {protocol}.txt")

# Main function to scrape proxies, check their working status, and save them
def scrape_and_check_proxies():
    all_proxies = []

    # Scrape proxies from all websites
    for site in PROXY_SITES:
        logging.info(f"Scraping proxies from {site}...")
        proxies = scrape_proxies(site)
        logging.info(f'Scraped {len(proxies)} proxies from {site}')
        all_proxies.extend(proxies)
    
    # Check proxies and categorize them by protocol
    working_proxies = {'http': [], 'https': [], 'socks4': [], 'socks5': []}
    
    # Using ThreadPoolExecutor to check proxies in parallel with progress bar
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_proxy, proxy, working_proxies): proxy for proxy in all_proxies}
        
        # Progress bar with tqdm
        for _ in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Checking Proxies"):
            pass  # Just progress the bar while futures are being completed

    # Save working proxies by protocol after the check is complete
    save_proxies(working_proxies)

# Run the script
if __name__ == "__main__":

    scrape_and_check_proxies()
