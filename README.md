# TailorAI Backend

A simple backend to scrape LinkedIn jobs using Apify and store them in MinIO object storage.

## Setup

### 1. Start MinIO Server

```bash
docker-compose up -d
```

This will start MinIO on:
- **API**: http://localhost:9000
- **Console**: http://localhost:9001

Login credentials:
- Username: `minioadmin`
- Password: `minioadmin`

### 2. Install Python Dependencies

```bash
pip install apify-client minio pydantic pydantic-settings
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```env
APIFY_TOKEN=your_apify_token_here
LINKEDIN_URL=your_linkedin_search_url_here
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=scraped-jobs
MINIO_SECURE=False
```

### 4. Run the Scraper

```bash
cd backend
python scrape.py
```

## How It Works

1. **Scraping**: The script uses Apify to scrape LinkedIn jobs based on your search URL
2. **Storage**: Results are uploaded to MinIO with date-based partitioning
3. **Partitioning**: Files are organized by ingestion date: `YYYY/MM/DD/jobs_YYYYMMDD_HHMMSS.json`

## Accessing MinIO

Visit http://localhost:9001 to access the MinIO console and browse your scraped data.

## Project Structure

```
TailorAI/
├── backend/
│   ├── scrape.py          # Main scraping script
│   ├── settings.py        # Configuration management
│   └── scraped_jobs.json  # (deprecated - now using MinIO)
├── docker-compose.yml     # MinIO server configuration
├── .env                   # Environment variables
└── README.md
```
