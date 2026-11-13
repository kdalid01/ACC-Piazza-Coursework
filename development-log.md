# Piazza Development Log

**Repository:** [ACC-Piazza-Coursework](https://github.com/kdalid01/ACC-Piazza-Coursework)

## Milestone 1 — Initial Setup
**4 November 2026**

- Created and cloned my GitHub repository.
- Set up Python, FastAPI and the virtual environment.
- Created and tested the `/health` endpoint.
- Added README, requirements and `.gitignore`.

**Sources:** Week 1 labs.

---

## Milestone 2 — Application Development

### 13 November 2026 — Database Setup

- Set up SQLite and SQLAlchemy using the Week 3 examples.
- Created the User model and `seed.py`.
- Created the database and checked the table.
- Kept the database code in separate files, as shown in the labs.

**Sources:** Week 3, Part 1. 

### 13 November 2026 — FastAPI and Pydantic

- Added `get_db()` to connect FastAPI to the database.
- Created a temporary `/users` endpoint.
- Added `schemas.py` to control what user data is returned.
- Excluded password hashes from API responses.

**Sources:** Week 3, Parts 2–3. 

### 13 November 2026 — Post API and Automated Testing

- Added the Post model, Pydantic schemas and endpoints for creating and retrieving posts.
- Moved the FastAPI routes into `application.py` to make testing easier.
- Added three unit test cases for post expiry boundaries.
- Added five API tests covering creation, retrieval, validation, missing posts and database persistence.
- Used temporary SQLite databases to keep tests independent.
- Fixed an import error in `application.py`.

**Testing:** `python -m pytest -v` — 8 passed (3 unit cases, 5 API tests).

**Sources:** Week 3, Parts 2–3 and Weekend Activity. I used chatGPT to explain testing and troubleshoot errors. The explanations helped me understand why errors occurred and how to fix them independently.









