from fastapi import FastAPI

app = FastAPI(title="Piazza API")


@app.get("/health")
def health():
    return {"status": "healthy"}