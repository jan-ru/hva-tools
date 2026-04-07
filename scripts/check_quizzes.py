"""Quick check: print what extract_quizzes finds in the fixture."""

from pathlib import Path
from playwright.sync_api import sync_playwright
from brightspace_extractor.extraction import extract_quizzes

pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True)
page = browser.new_page()
page.goto(Path("tests/quizzes-debug.html").resolve().as_uri())
results = extract_quizzes(page)
browser.close()
pw.stop()

for r in results:
    print(f'    "{r["quiz_id"]}": "{r["name"]}",')
print(f"\nTotal: {len(results)}")
