# Piazza API

The Piazza application is a backend discussion platform developed as part of the Advanced Cloud Computing coursework.

## Technologies
- Python
- FastAPI
- SQLite 
- ...

## Local setup

Create a virtual environment:

python -m venv .venv

Activate it on Windows:

.venv\Scripts\Activate.ps1

Install dependencies:

python -m pip install -r requirements.txt

## Run the API

python -m uvicorn main:app --reload

API documentation:
http://127.0.0.1:8000/docs

Health endpoint:
http://127.0.0.1:8000/health

## Development status

Milestone 1: Initial FastAPI application and health endpoint.