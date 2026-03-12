import json
from datetime import date, datetime
from typing import Any, Dict, Optional


def parse_raw_json(raw_json: str) -> dict:
    """Parse raw Apify JSON string and extract/flatten fields into Silver schema."""
    job = json.loads(raw_json)

    # Extract company address (flatten)
    address = job.get("companyAddress", {}) or {}

    return {
        # Core identifiers
        "id": job.get("id"),
        "tracking_id": job.get("trackingId"),

        # Job details
        "title": job.get("title"),
        "description_text": job.get("descriptionText"),
        "description_html": job.get("descriptionHtml"),
        "seniority_level": job.get("seniorityLevel"),
        "employment_type": job.get("employmentType"),
        "job_function": job.get("jobFunction"),
        "industries": job.get("industries"),

        # Company info
        "company_name": job.get("companyName"),
        "company_linkedin_url": job.get("companyLinkedinUrl"),
        "company_logo": job.get("companyLogo"),
        "company_website": job.get("companyWebsite"),
        "company_description": job.get("companyDescription"),
        "company_slogan": job.get("companySlogan"),
        "company_employees_count": job.get("companyEmployeesCount"),

        # Flattened address
        "company_street_address": address.get("streetAddress"),
        "company_city": address.get("addressLocality"),
        "company_state": address.get("addressRegion"),
        "company_postal_code": address.get("postalCode"),
        "company_country": address.get("addressCountry"),

        # Location & salary
        "location": job.get("location"),
        "salary": job.get("salary"),
        "salary_info": job.get("salaryInfo"),

        # Posting info
        "posted_at": job.get("postedAt"),
        "applicants_count": job.get("applicantsCount"),

        # URLs
        "link": job.get("link"),
        "apply_url": job.get("applyUrl"),
        "input_url": job.get("inputUrl"),

        # Job poster info (optional)
        "job_poster_name": job.get("jobPosterName"),
        "job_poster_title": job.get("jobPosterTitle"),
        "job_poster_profile_url": job.get("jobPosterProfileUrl"),

        # Benefits
        "benefits": job.get("benefits"),
    }


def clean_value(val: Any) -> Any:
    """Clean value for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val

def map_job_record(source_data: Dict[str, Any], is_active: bool = True) -> Dict[str, Any]:
    """
    Map a raw job dictionary (from Silver or Scraper) to the Supabase 'jobs' table schema.
    
    Args:
        source_data: Dictionary containing job fields (keys match Silver schema).
        is_active: Status of the job (default True/active).
    
    Returns:
        Dictionary matching Supabase 'jobs' table columns.
    """
    # Defensive .get in case source keys vary slightly
    
    return {
        "id": str(source_data.get("id")),
        "company_name": source_data.get("company_name"),
        "title": source_data.get("title"),
        "location": source_data.get("location"),
        "description_text": source_data.get("description_text"),
        # Prefer 'link' (Silver) or 'job_url'
        "job_url": source_data.get("link") or source_data.get("job_url"),
        "posted_at": clean_value(source_data.get("posted_at")),
        "seniority_level": source_data.get("seniority_level"),
        "employment_type": source_data.get("employment_type"),
        "applicants_count": source_data.get("applicants_count"),
        "company_website": source_data.get("company_website"),
        
        # New Fields
        "job_function": source_data.get("job_function"), # JSON
        "industries": source_data.get("industries"), # JSON
        "salary_info": source_data.get("salary_info"),
        "salary_min": None,
        "salary_max": None,
        "benefits": source_data.get("benefits"), # JSON
        
        "company_linkedin_url": source_data.get("company_linkedin_url"),
        "company_logo": source_data.get("company_logo"),
        "company_description": source_data.get("company_description"),
        "company_slogan": source_data.get("company_slogan"),
        "company_employees_count": source_data.get("company_employees_count"),
        "company_city": source_data.get("company_city"),
        "company_state": source_data.get("company_state"),
        "company_country": source_data.get("company_country"),
        "company_postal_code": source_data.get("company_postal_code"),
        "company_street_address": source_data.get("company_street_address"),
        
        "job_poster_name": source_data.get("job_poster_name"),
        "job_poster_title": source_data.get("job_poster_title"),
        "job_poster_profile_url": source_data.get("job_poster_profile_url"),
        
        "apply_url": source_data.get("apply_url"),
        "input_url": source_data.get("input_url"),
        
        "status": "active" if is_active else "archived", 
        "updated_at": datetime.now().isoformat() 
    }
