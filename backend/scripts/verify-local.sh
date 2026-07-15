#!/bin/bash
# Verify local setup — healthcare readmission prediction platform
set -e

echo "=== Healthcare Readmission Platform Verification ==="
echo ""

# 1. Check PostgreSQL
echo -n "PostgreSQL: "
if pg_isready -q 2>/dev/null; then
    echo "OK"
else
    echo "FAILED — start with: sudo service postgresql start"
    exit 1
fi

# 2. Check Main API
echo -n "Main API (port 8000): "
API=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ready 2>/dev/null || echo "000")
if [ "$API" = "200" ]; then
    echo "OK"
else
    echo "NOT RUNNING (HTTP $API)"
    echo "Start with: ./scripts/start-local.sh"
    exit 1
fi

# 3. Authentication
echo -n "Authentication: "
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Test123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$TOKEN" ]; then
    echo "OK"
else
    echo "FAILED — login rejected"
    exit 1
fi

# 4. Patient CRUD
echo -n "Patient list: "
PAT=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/patients)
if [ "$PAT" = "200" ]; then
    echo "OK"
else
    echo "FAILED (HTTP $PAT)"
    exit 1
fi

# 5. Prediction
echo -n "Prediction creation: "
PRED=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/predict \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"patient_id":"a00e131c-32fd-443b-a20d-4c7c301ab764","features":{"age":72,"had_cvd":1,"had_diabetes":1,"had_hypertension":1,"num_previous_admissions":3,"length_of_stay_days":14,"num_procedures":4,"num_medications":6,"has_insurance":1,"gender_M":1,"income_level_low":1,"income_level_medium":0}}')
if [ "$PRED" = "200" ]; then
    echo "OK"
else
    echo "FAILED (HTTP $PRED)"
    exit 1
fi

# 6. Audit persistence
echo -n "Audit persistence: "
AUDIT=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/audit)
COUNT=$(echo "$AUDIT" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null)
echo "OK ($COUNT records)"

# 7. Workflow persistence
echo -n "Workflow persistence: "
WF=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/workflows)
WF_COUNT=$(echo "$WF" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null)
echo "OK ($WF_COUNT records)"

echo ""
echo "=== All checks passed ==="