import argparse
import json
from web_crawler import WebCrawler, generate_html_report
import datetime
import os

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Web Crawler for Broken Link Detection')
    parser.add_argument('--start_url', required=True, help='Starting URL for crawling')
    parser.add_argument('--exclude', nargs='*', default=[], help='URL patterns to exclude (space separated)')
    parser.add_argument('--max_pages', type=int, default=100, help='Maximum number of pages to crawl')
    parser.add_argument('--concurrency', type=int, default=10, help='Number of concurrent requests')
    parser.add_argument('--output_dir', default='reports', help='Directory to store reports')
    
    args = parser.parse_args()
    
    print(f"Starting crawler at: {args.start_url}")
    print(f"Excluding patterns: {args.exclude}")
    print(f"Max pages: {args.max_pages}")
    print(f"Concurrency: {args.concurrency}")
    
    # Run the crawler
    crawler = WebCrawler(
        start_url=args.start_url,
        exclude_patterns=args.exclude,
        max_pages=args.max_pages,
        concurrency=args.concurrency
    )
    
    broken_links = crawler.crawl()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate report
    scan_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_report = generate_html_report(broken_links, args.start_url, scan_date)
    
    # Save reports
    date_prefix = datetime.datetime.now().strftime("%Y-%m-%d")
    html_file = os.path.join(args.output_dir, f"{date_prefix}_broken_links_report.html")
    json_file = os.path.join(args.output_dir, f"{date_prefix}_broken_links_data.json")
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(broken_links, f, indent=2)
    
    print(f"Crawl completed. Found {len(broken_links)} broken links.")
    print(f"HTML report saved to: {html_file}")
    print(f"JSON data saved to: {json_file}")

if __name__ == "__main__":
    main()
