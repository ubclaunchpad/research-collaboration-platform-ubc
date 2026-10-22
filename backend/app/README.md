# FastAPI Setup

## Health Check
The backend provides a `/health` endpoint to verify that the FastAPI server is running correctly.

### Test the endpoint
Start the backend server:

cd backend
uv run fastapi dev

In another terminal, run:

curl http://127.0.0.1:8000/health

or test endpoint on your local browser:

http://127.0.0.1:8000/health 

**Expected response:**

```json
{
  "status": "ok"
}
```
