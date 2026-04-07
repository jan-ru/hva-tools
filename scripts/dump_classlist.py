"""Dump the classlist HTML for a class to tests/classlist-debug.html."""

import time

from brightspace_extractor.browser import connect_to_browser

browser, ctx, page = connect_to_browser("http://localhost:9222")
page.goto(
    "https://dlo.mijnhva.nl/d2l/lms/classlist/classlist.d2l?ou=698557",
    wait_until="networkidle",
)
time.sleep(3)

# Select 200 per page to get all students
sel = page.locator("select[name='gridUsers_sl_pgS2']")
if sel.count() > 0:
    sel.first.select_option("200")
    page.wait_for_load_state("networkidle")
    time.sleep(5)

page.wait_for_load_state("domcontentloaded")
time.sleep(2)

html = page.content()
with open("tests/classlist-debug.html", "w", encoding="utf-8") as f:
    f.write(html)

browser.close()
print("Saved to tests/classlist-debug.html")
