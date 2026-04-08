"""Dump the quizzes HTML for a class to tests/quizzes-debug.html."""

import time

from brightspace_extractor.browser import connect_to_browser

browser, ctx, page = connect_to_browser("http://localhost:9222")
page.goto(
    "https://dlo.mijnhva.nl/d2l/lms/quizzing/admin/quizzes_manage.d2l?ou=698557",
    wait_until="networkidle",
)
time.sleep(5)

page.wait_for_load_state("domcontentloaded")
time.sleep(2)

html = page.content()
with open("tests/quizzes-debug.html", "w", encoding="utf-8") as f:
    f.write(html)

browser.close()
print("Saved to tests/quizzes-debug.html")
