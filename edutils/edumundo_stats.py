#!/usr/bin/env python3

import csv
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import Page

from bs4 import BeautifulSoup

import config
from scraping_utils import BrowserManager, PatternExtractor, ScrapingSession, SelectorFinder

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@dataclass
class ModuleStats:
    class_name: str
    module_name: str
    submodule_name: str
    progress: float
    completion_rate: float
    average_score: float
    total_students: int
    last_activity: str


@dataclass
class ExtractionResult:
    extraction_date: str
    extraction_time: str
    class_name: str
    module_name: str
    time_spent_minutes: Optional[int] = None
    progress_percentage: Optional[int] = None
    assignments_completed: Optional[int] = None
    assignments_total: Optional[int] = None
    assignments_percentage: Optional[float] = None
    quizzes_completed: Optional[int] = None
    quizzes_total: Optional[int] = None
    quizzes_percentage: Optional[float] = None


class EduMundoStatsReader:
    """Main class for reading statistics from EduMundo"""

    def __init__(self, url: str):
        self.url = url
        self.session = ScrapingSession(config.CHROME_DEBUG_PORT)
        self.extractor = PatternExtractor()

    def set_use_existing_session(self, use_existing: bool = True):
        self.session.browser_manager.use_existing_session = use_existing

    def extract_stats_for_combination(self, module_value: str, class_value: str) -> Optional[Dict[str, Any]]:
        """Extract statistics for a specific module and class combination"""
        try:
            page = self.session.connect_to_existing_browser("edumundo")
            if not page:
                return None

            self.session.select_option_and_wait(page, config.MODULE_SELECTOR, module_value, config.MODULE_WAIT_MS)
            self.session.select_option_and_wait(page, config.CLASS_SELECTOR, class_value, config.CLASS_WAIT_MS)

            return self._extract_current_stats(page)

        except Exception as e:
            log.error("Error extracting stats for combination: %s", e)
            return None

    def _extract_current_stats(self, page: Page) -> Dict[str, Any]:
        """Extract current statistics from the page"""
        try:
            soup = self.session.wait_and_extract(page, 2000)

            stats: Dict[str, Any] = {}
            stats['time_spent_minutes'] = self.extractor.extract_time_duration(soup)
            stats['progress_percentage'] = self.extractor.extract_percentage(soup, r'voortgang van (\d+)%')

            stats['assignments_completed'], stats['assignments_total'], stats['assignments_percentage'] = \
                self.extractor.extract_completion_ratio(soup, 'opdrachten')

            stats['quizzes_completed'], stats['quizzes_total'], stats['quizzes_percentage'] = \
                self.extractor.extract_completion_ratio(soup, 'quizzen')

            log.debug("Extracted stats: %s", stats)
            return stats

        except Exception as e:
            log.error("Error extracting current stats: %s", e)
            return {}

    def get_available_options(self) -> Tuple[List[Dict], List[Dict]]:
        """Get available module and class options from the page"""
        try:
            page = self.session.connect_to_existing_browser("edumundo")
            if not page:
                return [], []

            soup = self.session.wait_and_extract(page, 1000)

            modules = self.extractor.extract_select_options(soup, config.MODULE_SELECTOR)
            classes = self.extractor.extract_select_options(soup, config.CLASS_SELECTOR)

            return modules, classes

        except Exception as e:
            log.error("Error getting available options: %s", e)
            return [], []


class EduStatsApp:
    """Main application class"""

    def __init__(self, url: str):
        self.reader = EduMundoStatsReader(url)
        self.connection_method = None

    def setup_connection_method(self) -> bool:
        """Choose how to connect to the browser"""
        print("\n=== Browser Connection Method ===")
        print("1. Connect to existing authenticated browser session (Recommended)")
        print("2. Launch new browser (requires manual login)")

        choice = input("Choose connection method (1-2): ").strip()

        if choice == "1":
            self._setup_existing_session()
            return True
        elif choice == "2":
            self._setup_new_browser()
            return True
        else:
            print("Invalid choice")
            return False

    def _setup_existing_session(self):
        """Setup existing session connection"""
        print("\nTo use existing session, please:")
        print('1. Start Chrome with: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"'
              ' --remote-debugging-port=9222 --remote-allow-origins="*" --user-data-dir=/tmp/chrome-debug')
        print("2. Navigate to HVA EduMundo and log in")
        print("3. Go to the statistics page")
        print("4. Come back here and continue")

        confirm = input("\nHave you completed the above steps? (y/n): ").strip().lower()
        if confirm == 'y':
            self.reader.set_use_existing_session(True)
            self.connection_method = 'existing_session'
            log.info("Will connect to existing browser session")
        else:
            print("Please complete the setup and try again")

    def _setup_new_browser(self):
        """Setup new browser connection"""
        print("\nWill launch new browser - you'll need to handle login manually")
        self.reader.set_use_existing_session(False)
        self.connection_method = 'new_browser'

    def _ensure_connection(self) -> bool:
        """Ensure connection is established"""
        if not self.connection_method:
            print("Please setup browser connection first (option 1)")
            return False
        return True

    def automate_all_extractions(self):
        """Automate extraction of statistics for all classes and modules"""
        log.info("Starting automated extraction...")

        modules, classes = self.reader.get_available_options()
        if not modules or not classes:
            log.error("Failed to get available options")
            return

        log.info("Found %d modules and %d classes", len(modules), len(classes))
        log.info("Total combinations to process: %d", len(modules) * len(classes))

        results = self._process_all_combinations(modules, classes)
        self._save_results(results)
        log.info("Completed! Extracted data for %d combinations", len(results))

    def _process_all_combinations(self, modules: List[Dict], classes: List[Dict]) -> List[ExtractionResult]:
        """Process all module/class combinations"""
        results = []
        total_combinations = len(modules) * len(classes)
        current = 0

        for module in modules:
            for class_item in classes:
                current += 1
                log.info("Processing %d/%d: %s - %s", current, total_combinations,
                         class_item['name'], module['name'])

                stats = self.reader.extract_stats_for_combination(module['value'], class_item['value'])
                if stats:
                    result = self._create_extraction_result(stats, module['name'], class_item['name'])
                    results.append(result)

                time.sleep(config.REQUEST_DELAY)

        return results

    def _create_extraction_result(self, stats: Dict, module_name: str, class_name: str) -> ExtractionResult:
        """Create ExtractionResult from stats dictionary"""
        now = datetime.now()
        return ExtractionResult(
            extraction_date=now.strftime('%Y-%m-%d'),
            extraction_time=now.strftime('%H:%M:%S'),
            class_name=class_name,
            module_name=module_name,
            **{k: v for k, v in stats.items() if v is not None}
        )

    def quick_test_extraction(self):
        """Quick test: extract data for 'Toon alle modules' for two classes"""
        log.info("Starting quick test extraction for two classes...")

        test_combinations = [
            {"module_value": "", "module_name": "Toon alle modules", "class_value": "9823", "class_name": "FA1E"},
            {"module_value": "", "module_name": "Toon alle modules", "class_value": "9819", "class_name": "FA1A"}
        ]

        results = []
        for combo in test_combinations:
            log.info("Extracting: %s - %s", combo['class_name'], combo['module_name'])

            stats = self.reader.extract_stats_for_combination(combo['module_value'], combo['class_value'])
            if stats:
                result = self._create_extraction_result(stats, combo['module_name'], combo['class_name'])
                results.append(result)
                log.debug("Success: %s", stats)

        self._save_results(results)
        log.info("Quick test completed! Results: %d combinations", len(results))

    def _save_results(self, results: List[ExtractionResult]):
        """Save results to CSV file"""
        if not results:
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"automated_stats_{timestamp}.csv"

        fieldnames = [
            'extraction_date', 'extraction_time', 'class_name', 'module_name',
            'time_spent_minutes', 'progress_percentage', 'assignments_completed',
            'assignments_total', 'assignments_percentage', 'quizzes_completed',
            'quizzes_total', 'quizzes_percentage'
        ]

        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result.__dict__)

        log.info("CSV data saved to %s", filename)
        self._print_summary(results)

    def _print_summary(self, results: List[ExtractionResult]):
        """Print extraction summary"""
        if not results:
            return

        total_time = sum(r.time_spent_minutes or 0 for r in results)
        valid_progress = [r.progress_percentage for r in results if r.progress_percentage is not None]
        avg_progress = sum(valid_progress) / len(valid_progress) if valid_progress else 0

        log.info("Total time across all combinations: %dh %dm", total_time // 60, total_time % 60)
        log.info("Average progress across all combinations: %.1f%%", avg_progress)


def main():
    url = config.EDUMUNDO_URL
    app = EduStatsApp(url)

    print("EduMundo Module & Class Statistics Reader")
    print("=" * 50)

    if len(sys.argv) > 1:
        command = sys.argv[1]
        app.reader.set_use_existing_session(True)
        app.connection_method = 'existing_session'

        if command == "automate":
            log.info("Automation mode: Extracting data for all classes and modules...")
            app.automate_all_extractions()
        elif command == "quicktest":
            log.info("Quick test mode: Extracting data for 'Toon alle modules' and two classes...")
            app.quick_test_extraction()
        else:
            log.error("Unknown command: %s", command)
        return

    while True:
        print("\nOptions:")
        print("1. Setup browser connection")
        print("2. Run quick test (2 classes)")
        print("3. Run full automation (all combinations)")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            app.setup_connection_method()
        elif choice == "2":
            if app._ensure_connection():
                app.quick_test_extraction()
        elif choice == "3":
            if app._ensure_connection():
                app.automate_all_extractions()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
