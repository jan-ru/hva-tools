"""Shared expected data for fixture-based tests.

Both the Playwright fixture tests and the adapter fixture tests validate
against these values, keeping the ground truth in one place.
"""

EXPECTED_ASSIGNMENTS: dict[str, str] = {
    "336740": "Proces: Verslag en gesprek",
    "336761": "Beroepsproduct Management Accounting",
    "336741": "Data & Control Sprint 1 FC2A",
    "336753": "Data & Control Sprint 1 FC2C",
    "336743": "Data & Control Sprint 2 FC2A",
    "336748": "Data & Control Sprint 2 FC2C",
    "336744": "Data & Control Sprint 3 FC2A",
    "336749": "Data & Control Sprint 3 FC2C",
    "336727": "Groepscontract FC2A",
    "336729": "Groepscontract FC2C",
    "336731": "FC2A Feedbackformulier sprint 1",
    "336734": "FC2C Feedbackformulier sprint 1",
    "336735": "formulier en opdracht Individueel slb gesprek",
    "336754": "Goodhabitz persoonlijk leiderschap",
    "336736": "Groepsproces",
    "336737": "FC2A Feedbackformulier sprint 2",
    "336756": "FC2C Feedbackformulier sprint 2",
    "336730": "FC2A Feedbackformulier sprint 3",
    "336757": "FC2C Feedbackformulier sprint 3",
    "336747": "Onderzoek bij Data & Control cursus Zoeklicht Basis en Zoeklicht Gevorderd",
    "336762": "FC2A Presentatie onderzoekend vermogen bij les 3 onderzoekend vermogen",
    "336764": "FC2C Presentatie onderzoekend vermogen bij les 3 onderzoekend vermogen",
    "336750": "Beoordeling beroepsproduct FC2A",
    "336752": "Beoordeling beroepsproduct FC2C",
    "336739": "Procesverslag Data & Control",
    "336755": "Herkansing beroepsproduct Data & Control (Individueel)",
    "336758": "Beroepsproduct Data & Control (individueel)",
    "336760": "Power BI basis",
}

EXPECTED_CLASSLIST_TOTAL = 37

KNOWN_STUDENTS = [
    {"name": "Anwar Laroub", "org_defined_id": "500908250", "role": "Student"},
    {"name": "Bas Koot", "org_defined_id": "500978594", "role": "Student"},
    {"name": "Carmen Jordaan", "org_defined_id": "500948231", "role": "Student"},
]

KNOWN_LECTURERS = [
    {
        "name": "Diederik Ogilvie",
        "org_defined_id": "ogide",
        "role": "Designing Lecturer",
    },
    {
        "name": "Jan-Ru Muller",
        "org_defined_id": "jrmulle",
        "role": "Designing Lecturer",
    },
    {
        "name": "Joyce van Weering",
        "org_defined_id": "jweerin",
        "role": "Designing Lecturer",
    },
    {"name": "Paul te Riele", "org_defined_id": "riepc", "role": "Designing Lecturer"},
]

EXPECTED_GROUPS = [
    {"group_name": "FC2A - 1", "members": "4/4"},
    {"group_name": "FC2A - 2", "members": "4/4"},
    {"group_name": "FC2A - 3", "members": "4/4"},
    {"group_name": "FC2A - 4", "members": "4/4"},
    {"group_name": "FC2A - 5", "members": "3/4"},
    {"group_name": "FC2A - 6", "members": "4/4"},
    {"group_name": "FC2A - 7", "members": "3/4"},
    {"group_name": "FC2A - 8", "members": "2/4"},
]

EXPECTED_QUIZZES: dict[str, str] = {
    "72711": "Quiz week 1-2 MAC",
    "72712": "Quiz week 3 MAC",
    "72713": "Quiz week 4 MAC",
    "72714": "Quiz week 5 MAC",
    "72715": "Quiz week 6 MAC",
    "72716": "Quiz week 7A MAC",
    "72717": "Quiz week 7B MAC",
    "72718": "Quiz week 8 MAC",
    "72719": "MAC quiz (herhaling wk 1-wk 7)",
    "72720": "Quiz week 1-2 MAC",
    "72721": "Quiz week 3 MAC",
    "72722": "Quiz week 4 MAC",
    "72723": "Quiz week 5 MAC",
    "72724": "Quiz week 6 MAC",
    "72725": "Quiz week 7A MAC",
    "72726": "Quiz week 7B MAC",
    "72727": "Quiz week 8 MAC",
    "72728": "MAC quiz (herhaling wk 1-wk 7)",
    "72729": "Quiz 0 MIS week 2",
    "72733": "Quiz 2 MIS, week 7, variant 2",
    "72730": "Quiz 1 MIS, week 4, variant 1",
    "72731": "Quiz 1 MIS, week 4",
    "72732": "Quiz 2 MIS, week 7, variant 1",
    "72734": "Quiz 1 MIS, week 4, variant 2",
}

EXPECTED_RUBRICS: dict[str, str] = {
    "72528": "Assessment Eindberoepsproduct",
    "72538": "Assessment Eindberoepsproduct 2024-2025 (Individuele herkansing)",
    "72537": "Eindbeoordeling Beroepsproduct",
    "72539": "Eindbeoordeling Beroepsproduct (Individuele herkansing)",
    "72541": "Eindbeoordeling Management Accounting Beroepsproduct",
    "72530": "Eindbeoordeling sprint 1 D & C 2024-2025",
    "72531": "Eindbeoordeling sprint 2 D & C 2024-2025",
    "72532": "Eindbeoordeling sprint 3 D & C 2024-2025",
    "72540": "Herkansing beroepsproduct D&C (Individueel)",
    "72536": "PRO Individueel Portfolio",
    "72529": "Rubric Proces: verslag en gesprek 2025-2026",
    "72533": "Tussentijdse beoordeling Sprint 1 D & C 2025-2026",
    "72534": "Tussentijdse beoordeling sprint 2 D & C 2025-2026",
    "72535": "Tussentijdse beoordeling Sprint 3 D & C 2025-2026",
    "72542": "Untitled",
}
