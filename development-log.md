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


### 15 November 2026 — User Authentication and Post Authors

- Added user registration and login using password hashing and JWT authentication.
- Created `security.py` and an authentication router.
- Protected the post endpoints so users must log in before accessing them.
- Linked posts to their authors using a foreign key.
- Updated the Pydantic schemas for registration, login and authentication.
- Used environment variables to keep the JWT secret out of the source code.

**Sources:** Week 4 labs and Piazza coursework specification. I used ChatGPT to help understand JWT authentication, password hashing, and troubleshoot errors.

### 16 November 2026 — Post Topics, Expiry and Testing

- Added the four coursework topics: Politics, Health, Sport and Tech.
- Created a many-to-many relationship so posts can belong to multiple topics.
- Added filtering to retrieve posts by topic.
- Added validation for post titles, bodies and expiry timestamps.
- Implemented Live and Expired post status, including the exact expiry boundary.
- Added filtering to retrieve posts by status.
- Updated the API tests to use authentication tokens and the new post structure.
- Added tests checking that unauthenticated users cannot access posts and that `/health` remains public.
- Fixed indentation, import and variable errors while updating the application.

**Testing:** `python -m pytest -v` — 10 passed (3 expiry boundary tests and 7 API tests), 1 warning.

**Sources:** Week 3 and Week 4 labs, and the Piazza coursework specification. I used ChatGPT to help understand pytest fixtures, rxplain some error messages, and help with debugging issues in my test code (AI was used as a learning and troubleshooting aid).

### 17 November 2026 — Reactions and Comments

- Implemented a Reaction model to store likes and dislikes and link them to users and posts.
- Created an endpoint for adding or changing reactions.
- Made sure each user can only have one reaction per post. If they change their mind, the existing reaction is updated rather than adding another one.
- Implemented checks to stop users from liking or disliking their own posts, or reacting to expired posts.
- Created the Comment model and an endpoint for adding comments.
- Users can leave multiple comments, including on their own posts, but not once a post has expired.
- Updated the post responses to show comments alongside the like and dislike counts.

**Sources:** Piazza coursework specification and Week 3–4 labs. I used ChatGPT to help understand SQLAlchemy relationships, reaction logic, response schemas, and debug my code. 

### 18 November 2026 — Most-Active Posts and Automated Testing

- Implemented `GET /topics/{topic}/most-active` endpoint to find the most-active live post in a topic.
- Added ranking rules using the total number of likes and dislikes. If posts have the same score, the newer post wins, followed by the lowest post ID if the timestamps are also the same.
- Ensured expired posts  are ignored and the endpoint returns an empty list if there are no live posts.
- Added automated tests for reactions, comments, expiry restrictions and most-active ranking.
- Tested repeated and changing reactions, commenting on expired posts, invalid login details and JWT tokens.
- Added tests for ranking ties and checked that expired posts cannot win.
- Added tests for duplicate registration, incorrect passwords, invalid JWTs and expired JWTs.
- Fixed a FastAPI response validation error caused by the ranking endpoint returning `None` instead of a list.

**Sources:** Piazza coursework specification and Week 3–4 labs. I used ChatGPT to understand pytest assertions, and to help debug failed tests.

### 19 November 2026 — Database Integrity and Final Application Improvements

- Added a `CheckConstraint` to the Reaction model so the database only accepts like or dislike.
- Enabled foreign-key checks in SQLite to make sure the relationships between records are valid.
- Made comments store and return UTC timestamps consistent with posts.
- Updated `.gitignore` to exclude `.env` to not accidentally upload secrets to GitHub.
- Went through the coursework requirements to check that I had implemented all the main application features.
- Reviewed what still needs testing before moving on to Docker.

**Testing:** `python -m pytest --collect-only -q`. Pytest found 34 tests (28 API tests and 6 unit test cases), 1 warning. 

**Database limitation note:** The new database constraints apply to newly created tables. Existing tables would need to be updated separately.

**Sources:** Piazza coursework specification, Week 3–4 labs and SQLAlchemy/SQLite concepts from the module. I used ChatGPT for troubleshooting errors.

**Milestone 2 — Application Development:** Completed implementation of the required Piazza endpoints and main rules. Full automated testing to be covered in Milestone 3.

**Next steps:**
- Finish checking the tests against the TC01–TC20 scenarios and make a test matrix.
- Improve the expiry tests so they don't depend on the real system time.
- Finish Milestone 3 — Automated Testing.
- Start Milestone 4 — Docker containerisation.

