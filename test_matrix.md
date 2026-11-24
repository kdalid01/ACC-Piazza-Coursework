# Piazza API – Test Matrix

## 1. Overview

This file shows how my automated tests cover the requirements in the Advanced Cloud Computing coursework.

I used pytest for the unit tests and FastAPI TestClient for the API tests. The tests check that Piazza behaves as expected, including when users send invalid requests or try to interact with expired posts.

The tests use temporary SQLite databases so they do not change my development database. I also used a controllable clock to test post expiry without having to wait for real time to pass.

## 2. Coursework Scenario – TC01–TC20

The coursework provides 20 test cases involving four users: Olga, Nick, Mary and Nestor. These are covered by the integration test `test_tc_piazza_scenario in `tests/test_piazza_scenario.py`.

|ID|What is being tested|Expected result|
|---|---|---|
|TC01|Register Olga, Nick, Mary and Nestor|All four registrations succeed (201)|
|TC02|Log in all four users|Each receives a JWT token (200)|
|TC03|Access posts without a token|Request rejected (401)|
|TC04|Olga creates a Tech post|Post created (201)|
|TC05|Nick creates a Tech post|Post created (201)|
|TC06|Mary creates a Tech post|Post created (201)|
|TC07|Browse Tech posts|Three posts with no reactions or comments|
|TC08|Nick and Olga like Mary's post|Both likes accepted|
|TC09|Nestor likes Nick's post and dislikes Mary's|Both reactions accepted|
|TC10|Check reaction counts|Mary: 2 likes, 1 dislike; Nick: 1 like|
|TC11|Mary tries to like her own post|Rejected (403)|
|TC12|Nick and Olga each add two comments to Mary's post|Four comments created|
|TC13|Browse posts again|Correct counts and comments returned|
|TC14|Nestor creates a Health post|Post created (201)|
|TC15|Browse Health posts|Nestor's post returned|
|TC16|Mary comments on Nestor's Health post|Comment created (201)|
|TC17|Mary tries to react after the Health post expires|Rejected (409)|
|TC18|Read the expired Health post|Post and original comment still available|
|TC19|Browse expired Sport posts when none exist|Empty list returned|
|TC20|Find the most-active live Tech post|Mary's post returned|
**Result:** The TC01–TC20 integration test passed on 24 November 2026.

- Tests use a temporary SQLite database.
- Users authenticate using JWT bearer tokens.
- The test checks HTTP status codes and response data.
- For the Health post, I moved the application clock to its expiry time using pytest's `monkeypatch` fixture.
- I used a 17-day expiry period for the Tech posts to keep them live throughout the scenario.

## 3. Additional Required Tests

The coursework also asks for tests beyond the main scenario. I have grouped these by the part of the application being tested.

### Authentication

|What is being tested|Test function|Expected result|
|---|---|---|
|Registering with an email that already exists|`test_duplicate_registration`|409|
|Logging in with an incorrect password|`test_incorrect_password`|401|
|Using an invalid JWT|`test_invalid_token_rejected`|401|
|Using an expired JWT|`test_expired_token_rejected`|401|
|Accessing the health endpoint without a token|`test_health_does_not_require_authentication`|200|
|Accessing business endpoints without a token|`test_business_endpoints_require_authentication`|401 for all six requests|
The last test uses parameterisation to check six protected endpoints without repeating the same test code.

### Posts and validation

|What is being tested|Test function|Expected result|
|---|---|---|
|Retrieving posts from an empty database|`test_starts_empty`|Empty list|
|Creating and retrieving a post|`test_create_and_retrieve`|201, then 200|
|Retrieving a post that does not exist|`test_missing_post`|404|
|Creating a post with empty or whitespace-only text, empty topics or an invalid topic|`test_invalid_post_fields`|422 for all six cases|
|Creating a post with multiple topics|`test_post_with_multiple_topics`|Post appears under both topics|
|Filtering by an invalid topic|`test_invalid_topic_rejected`|422|
|Filtering by an invalid status|`test_invalid_status_filter_rejected`|422|
|Creating a post with an expiry timestamp without a timezone|`test_expiry_without_timezone_rejected`|422|
|Creating a post with an expiry time in the past|`test_post_expiry_in_past_rejected`|422|
|Filtering by topic and status together|`test_combined_topic_and_status_filter`|Correct live and expired posts returned|
I used parameterisation for the invalid post fields. This lets me check six different invalid inputs using the same test function.

The combined filtering test uses three posts with different topics and expiry times. Moving the clock forward checks that the API correctly filters live and expired posts.

### Reactions and comments

|What is being tested|Test function|Expected result|
|---|---|---|
|Repeating the same reaction and changing it|`test_repeated_and_switched_reactions`|Counts updated correctly|
|Reacting to a missing post|`test_reaction_to_missing_post`|404|
|Using an invalid reaction value|`test_invalid_reaction_value`|422|
|Adding a comment|`test_user_can_comment_on_post`|201; comment saved|
|Sending an empty or whitespace-only comment|`test_empty_comment_rejected`|422|
|Commenting on a missing post|`test_comment_on_missing_post`|404|
The TC01–TC20 scenario also covers successful likes and dislikes, reacting to own post, adding multiple comments and reacting after expiry. The separate tests above check cases that are not fully covered by the main scenario.

### Expiry and ranking

|What is being tested|Test function|Expected result|
|---|---|---|
|Post expiry before, at and after the boundary|`test_post_is_live_boundary`|Correct True/False values|
|Live or Expired status at the boundary|`test_post_expiry_boundary`|Correct status|
|Reactions and comments at the expiry boundary|`test_exact_expiry_boundary`|Accepted before expiry; rejected at and after expiry|
|Finding a post when no live posts exist in the topic|`test_most_active_empty_topic`|Empty list|
|Equal reaction counts|`test_most_active_newest_post_wins`|Newer post wins|
|Equal reaction counts and creation times|`test_most_active_lowest_id_wins`|Lowest ID wins|
|Excluding expired posts from ranking|`test_most_active_excludes_expired_posts`|Live post wins|
|A live post with zero reactions|`test_most_active_with_zero_reactions`|Post returned with zero likes and dislikes|
The first two expiry tests are direct unit tests in `tests/test_rules.py`. They check the expiry functions without making API requests. The remaining tests use FastAPI TestClient.

For the expiry boundary test, I use a fixed time and move the clock to one second before expiry, exactly at expiry and one second after expiry.

For the ranking tests, I check that the application considers the total number of reactions first. If the scores are equal, the newer post wins. If the creation times are also equal, the post with the lowest ID wins.

### Additional unit tests

I have also prepared two further unit tests to check application rules directly, without using the API. These tests belong in `tests/test_rules.py`. 

|What is being tested|Test function|Expected result|
|---|---|---|
|Counting likes and dislikes, including when a reaction changes|`test_reaction_counts`|Counts are recalculated correctly|
|Converting SQLite timestamps and timezone offsets to UTC|`test_as_utc_conversion`|Correct UTC timestamps|

### Database persistence

|What is being tested|Test function|Expected result|
|---|---|---|
|Data survives closing and reopening the application against the same SQLite database file|`test_data_survives_new_application`|Previously created user and post can be retrieved|
This test uses two application instances connected to the same temporary database file. It checks that the user can log in again and retrieve the post created earlier.

## 4. How to Run the Tests

All tests can be run from the project folder using:

`python -m pytest -v`

To run the unit tests separately:

`python -m pytest tests/test_rules.py -v`

To run the coursework scenario alone:

`python -m pytest tests/test_piazza_scenario.py -v`

To run the additional API tests:

`python -m pytest tests/test_api.py -v`

The tests are independent because pytest creates a temporary database for each test. This means previous tests should not affect later ones.

The tests use fixtures defined in `tests/conftest.py` to set up the test application and database.

## 5. Test Results

I ran the full test suite on 24 November 2026 after adding the final unit and validation tests.

All 48 tests passed, with no failures or skipped tests.

|Test group|Passed|Failed|Skipped|
|---|---|---|---|
|Unit tests (`test_rules.py`)|8|0|0|
|API tests (`test_api.py`)|39|0|0|
|Coursework scenario (`test_piazza_scenario.py`)|1|0|0|
|**Total**|**48**|**0**|**0**|

**Command used:**

`python -m pytest -v`

**Result:** 48 passed, 1 warning in 10.18 seconds.

I also ran the unit tests and API tests separately. All 8 unit tests passed, followed by all 40 API tests, including the TC01–TC20 scenario.

There was one `StarletteDeprecationWarning` about the use of `httpx` with Starlette's TestClient. This did not affect the tests, and no changes were needed for the coursework at this stage.

## 6. Limitations

The tests cover the main coursework scenario and the additional required cases, including invalid input, authentication, expiry and ranking.

The API tests use a local temporary SQLite database, so they do not prove that the application works in Docker or Kubernetes. These will be tested separately during deployment.

The persistence test checks that data survives restarting the application while using the same database file. It does not test recovery after a database or storage failure.

The expiry tests use a controlled clock rather than waiting for real time to pass. This makes the tests repeatable and allows the exact expiry boundary to be checked.
