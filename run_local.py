import sys

import uvicorn

sys.path.insert(0, "src")

if __name__ == "__main__":
    uvicorn.run("fact_verifier.main:app", host="127.0.0.1", port=8001, reload=True)
