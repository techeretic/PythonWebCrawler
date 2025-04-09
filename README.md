# PythonWebCrawler - Web Crawler for Broken Link Detection

This project provides a web crawler that detects broken links on your website. It's designed to run daily as an AWS Lambda function and generate reports in an S3 bucket.

## Features

- Crawls websites starting from a specified URL
- Detects broken links (HTTP 4xx, 5xx errors and connection failures)
- Excludes specified URL patterns from crawling
- Limits crawling to the same domain as the starting URL
- Uses concurrent requests for faster crawling
- Generates HTML reports of broken links
- Stores reports in an S3 bucket
- Runs automatically on a daily schedule

## Deployment Instructions

### Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9 or later
- Terraform (for infrastructure deployment)

### Step 1: Prepare the Lambda Package

1. Create a directory for your project:
   ```bash
   mkdir web-crawler && cd web-crawler
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Create a file named `lambda_function.py` and copy the web crawler code into it.

4. Install the required dependencies:
   ```bash
   pip install requests beautifulsoup4 boto3
   ```

5. Package the dependencies:
   ```bash
   pip install --target ./package requests beautifulsoup4 boto3
   cp lambda_function.py package/
   cd package
   zip -r ../web_crawler_lambda.zip .
   cd ..
   ```

### Step 2: Deploy the Infrastructure

1. Create a file named `main.tf` and copy the Terraform configuration into it.

2. Modify the variables in the Terraform configuration according to your needs:
   - `s3_bucket`: A unique name for the S3 bucket to store reports
   - `start_url`: The starting URL for crawling
   - `exclude_patterns`: URL patterns to exclude from crawling
   - `max_pages`: Maximum number of pages to crawl

3. Initialize Terraform:
   ```bash
   terraform init
   ```

4. Plan the deployment:
   ```bash
   terraform plan
   ```

5. Apply the configuration:
   ```bash
   terraform apply
   ```

### Step 3: Test the Deployment

1. Test the Lambda function by invoking it manually:
   ```bash
   aws lambda invoke --function-name web-crawler-broken-links --payload '{}' response.json
   ```

2. Check the CloudWatch Logs for the execution details.

3. Verify that the reports were generated in the S3 bucket:
   ```bash
   aws s3 ls s3://your-bucket-name/reports/
   ```

## Customization

### Environment Variables

You can modify these environment variables to adjust the crawler behavior:

- `START_URL`: The URL to start crawling from
- `EXCLUDE_PATTERNS`: JSON array of URL patterns to exclude
- `MAX_PAGES`: Maximum number of pages to crawl
- `S3_BUCKET`: S3 bucket name for reports

### Scheduling

The default schedule is set to run daily at 1:00 AM UTC. You can modify the `schedule_expression` in the `aws_cloudwatch_event_rule` resource to change this schedule.

### Resource Allocation

You can adjust the Lambda function's `timeout` and `memory_size` in the `aws_lambda_function` resource depending on the size of your website.

## Monitoring

- Lambda execution logs are available in CloudWatch Logs
- Daily reports are stored in the S3 bucket under the `reports/YYYY-MM-DD/` prefix
- Each run generates both an HTML report for human readability and a JSON data file for programmatic access

## Troubleshooting

- If the Lambda function times out, increase the `timeout` value and/or `memory_size`
- If crawling is too slow, increase the `concurrency` parameter in the WebCrawler initialization
- If the crawler is missing pages, check the `exclude_patterns` to ensure important paths aren't being excluded
- If the crawler is processing too many pages, decrease the `max_pages` parameter
