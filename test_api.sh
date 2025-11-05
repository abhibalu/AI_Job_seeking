#!/bin/bash
set -e

API="http://localhost:8000"

echo "=== Testing Resume API ==="

# 1. Get base resume
echo -e "\n1. GET /resume (base)"
curl -s "$API/resume" | jq '.basics.name'

# 2. Create a test variant
echo -e "\n2. POST /variants (create variant)"
curl -s -X POST "$API/variants" \
  -H 'Content-Type: application/json' \
  -d '{
    "variant_name": "abhijith_sivadas_moothedath_test_company",
    "company_name": "test_company",
    "tailored_resume": {
      "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
      "basics": {
        "name": "Abhijith Sivadas Moothedath",
        "label": "Data Engineer - Test Company",
        "email": "test@example.com"
      },
      "work": [],
      "education": [],
      "skills": []
    }
  }' | jq .

# 3. Get variant
echo -e "\n3. GET /variants/{name}"
curl -s "$API/variants/abhijith_sivadas_moothedath_test_company" | jq '.company_name'

# 4. Export PDF
echo -e "\n4. POST /export (generate PDF)"
curl -s -X POST "$API/export?variant_name=abhijith_sivadas_moothedath_test_company&fmt=pdf" -o /dev/null
echo "PDF generated"

# 5. Check PDF exists
echo -e "\n5. Verify PDF file"
ls -lh out/abhijith_sivadas_moothedath_test_company/Abhijith_sivadas_moothedath_test_company.pdf

# 6. Approve variant
echo -e "\n6. POST /ui/approve/{name}"
curl -s -X POST "$API/ui/approve/abhijith_sivadas_moothedath_test_company" -o /dev/null
echo "Approved"

# 7. List approved
echo -e "\n7. GET /approved"
curl -s "$API/approved" | jq .

# 8. Get status
echo -e "\n8. GET /status/{name}"
curl -s "$API/status/abhijith_sivadas_moothedath_test_company" | jq .

# 9. Download PDF (n8n endpoint)
echo -e "\n9. GET /variants/{name}/pdf"
curl -s "$API/variants/abhijith_sivadas_moothedath_test_company/pdf" -o /tmp/test_resume.pdf
ls -lh /tmp/test_resume.pdf

echo -e "\n=== All tests passed! ==="
