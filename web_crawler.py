import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import boto3
import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebCrawler:
    def __init__(self, start_url, exclude_patterns=None, max_pages=100, concurrency=10):
        """
        Initialize the web crawler
        
        Args:
            start_url (str): The URL to start crawling from
            exclude_patterns (list): List of URL patterns to exclude from crawling
            max_pages (int): Maximum number of pages to crawl
            concurrency (int): Number of concurrent requests
        """
        self.start_url = start_url
        self.domain = urlparse(start_url).netloc
        self.visited_urls = set()
        self.urls_to_visit = [start_url]
        self.broken_links = []
        self.exclude_patterns = exclude_patterns or []
        self.max_pages = max_pages
        self.concurrency = concurrency
    
    def should_exclude(self, url):
        """Check if URL should be excluded based on patterns"""
        parsed_url = urlparse(url)
        
        # Skip external domains
        if parsed_url.netloc and parsed_url.netloc != self.domain:
            return True
            
        # Skip URLs matching exclude patterns
        for pattern in self.exclude_patterns:
            if pattern in url:
                return True
                
        # Skip common non-HTML resources
        path = parsed_url.path.lower()
        if path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.doc', '.docx')):
            return True
            
        return False
    
    def check_url(self, url):
        """Check if a URL is valid and get all links from it"""
        try:
            headers = {'User-Agent': 'WebCrawler/1.0'}
            response = requests.get(url, timeout=10, headers=headers)
            status_code = response.status_code
            
            # Handle redirects
            if 300 <= status_code < 400:
                redirect_url = response.headers.get('Location')
                if redirect_url:
                    absolute_redirect = urljoin(url, redirect_url)
                    logger.info(f"Redirect: {url} -> {absolute_redirect}")
                    return status_code, []
            
            # Handle 404s and other errors
            if status_code >= 400:
                logger.warning(f"Broken link found: {url} (Status: {status_code})")
                return status_code, []
            
            # Only parse HTML content
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                return status_code, []
            
            # Extract links from HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                
                # Skip fragment identifiers within the same page
                if absolute_url.split('#')[0] == url:
                    continue
                    
                # Normalize the URL
                parsed = urlparse(absolute_url)
                normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    normalized_url += f"?{parsed.query}"
                
                if not self.should_exclude(normalized_url):
                    links.append(normalized_url)
            
            return status_code, links
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking {url}: {str(e)}")
            return None, []
    
    def crawl(self):
        """Crawl the website and find broken links"""
        while self.urls_to_visit and len(self.visited_urls) < self.max_pages:
            # Get a batch of URLs to process
            batch = []
            while self.urls_to_visit and len(batch) < self.concurrency:
                url = self.urls_to_visit.pop(0)
                if url not in self.visited_urls:
                    batch.append(url)
                    self.visited_urls.add(url)
            
            if not batch:
                break
                
            logger.info(f"Crawling batch of {len(batch)} URLs. Total visited: {len(self.visited_urls)}")
            
            # Process the batch concurrently
            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                results = list(executor.map(lambda url: (url, self.check_url(url)), batch))
            
            # Process results
            for url, (status_code, links) in results:
                if status_code is None or status_code >= 400:
                    referring_pages = [page for page in self.visited_urls if page != url]
                    self.broken_links.append({
                        'url': url,
                        'status_code': status_code,
                        'referred_from': referring_pages[:5]  # Limit to 5 referring pages
                    })
                
                # Add new URLs to visit
                for link in links:
                    if link not in self.visited_urls and link not in self.urls_to_visit:
                        self.urls_to_visit.append(link)
        
        logger.info(f"Crawl completed. Visited {len(self.visited_urls)} URLs, found {len(self.broken_links)} broken links.")
        return self.broken_links

def generate_html_report(broken_links, start_url, scan_date):
    """Generate an HTML report of broken links"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Broken Links Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .status-error {{ color: #d9534f; }}
            .status-warning {{ color: #f0ad4e; }}
        </style>
    </head>
    <body>
        <h1>Web Crawler: Broken Links Report</h1>
        <div class="summary">
            <p><strong>Start URL:</strong> {start_url}</p>
            <p><strong>Scan Date:</strong> {scan_date}</p>
            <p><strong>Total Broken Links Found:</strong> {len(broken_links)}</p>
        </div>
        
        <h2>Broken Links</h2>
        
        <table>
            <tr>
                <th>URL</th>
                <th>Status</th>
                <th>Referred From</th>
            </tr>
    """
    
    for link in broken_links:
        status_class = "status-error" if link['status_code'] >= 400 else "status-warning"
        referring = "<br>".join(link['referred_from'][:5]) if link['referred_from'] else "N/A"
        status = link['status_code'] if link['status_code'] else "Connection Error"
        
        html += f"""
            <tr>
                <td>{link['url']}</td>
                <td class="{status_class}">{status}</td>
                <td>{referring}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html

def save_to_s3(content, bucket_name, key, content_type='text/html'):
    """Save content to S3 bucket"""
    s3 = boto3.client('s3')
    s3.put_object(
        Body=content,
        Bucket=bucket_name,
        Key=key,
        ContentType=content_type
    )
    return f"s3://{bucket_name}/{key}"

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    try:
        # Get configuration from environment or event
        start_url = event.get('start_url') or os.environ.get('START_URL')
        exclude_patterns = event.get('exclude_patterns') or json.loads(os.environ.get('EXCLUDE_PATTERNS', '[]'))
        max_pages = int(event.get('max_pages') or os.environ.get('MAX_PAGES', '100'))
        s3_bucket = event.get('s3_bucket') or os.environ.get('S3_BUCKET')
        
        if not start_url:
            return {
                'statusCode': 400,
                'body': 'start_url is required'
            }
        
        if not s3_bucket:
            return {
                'statusCode': 400,
                'body': 's3_bucket is required'
            }
        
        # Initialize and run the crawler
        crawler = WebCrawler(
            start_url=start_url,
            exclude_patterns=exclude_patterns,
            max_pages=max_pages
        )
        
        broken_links = crawler.crawl()
        
        # Generate report
        scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_report = generate_html_report(broken_links, start_url, scan_date)
        
        # Save report to S3
        date_prefix = datetime.datetime.now().strftime("%Y-%m-%d")
        report_key = f"reports/{date_prefix}/broken_links_report.html"
        json_key = f"reports/{date_prefix}/broken_links_data.json"
        
        s3_html_path = save_to_s3(html_report, s3_bucket, report_key)
        s3_json_path = save_to_s3(json.dumps(broken_links), s3_bucket, json_key, 'application/json')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Crawler completed. Found {len(broken_links)} broken links.',
                'html_report': s3_html_path,
                'json_data': s3_json_path,
                'broken_links_count': len(broken_links)
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Error: {str(e)}"
        }
