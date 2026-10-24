"""Offline tests for the apply assistant. Labels are real ones seen on live forms (2026-10-23)."""
import tomllib
import unittest
from pathlib import Path

from apply.fill import FORBIDS_TOOLS_RE, answer, pick_option
from apply.queue import score

PROFILE = tomllib.loads((Path(__file__).parent.parent / "apply" / "profile.example.toml").read_text(encoding="utf-8"))
PROFILE["contact"].update(first_name="Test", last_name="Applicant", email="t@example.com", phone="5125550100",
                          location="Austin, TX")
PROFILE["education"].update(school="The University of Texas at Austin", degree="Bachelor's",
                            major="Computer Science", grad_month="May", grad_year="2028")


class TestAnswers(unittest.TestCase):
    def a(self, label, kind="text"):
        return answer(label, kind, PROFILE)

    def test_basics(self):
        self.assertEqual(self.a("First Name*"), "Test")
        self.assertEqual(self.a("Full name ✱"), "Test Applicant")
        self.assertEqual(self.a("Location (City)*"), "Austin, TX")
        self.assertEqual(self.a("Will you require Visa Sponsorship now, or in the future?*"), "No")

    def test_rule_order(self):
        # these were mis-answered when entity rules ran first
        self.assertEqual(self.a("Are you currently enrolled at an educational institution (e.g. college, university, bootcamp)?"), "Yes")
        self.assertEqual(self.a("When do you expect to complete your current degree program? Please provide your expected graduation month and year."), "May 2028")
        self.assertIsNone(self.a("Do you expect to graduate between December 2027 and June 2028?*"))

    def test_compound_questions_left_to_applicant(self):
        self.assertIsNone(self.a("This role requires you to already be legally authorized to work in the countries listed "
                                 "in the job posting without sponsorship. Are you?"))
        self.assertIsNone(self.a("Do you live in, and are you legally authorized to work in the countries listed in the job posting?"))

    def test_applicant_only(self):
        for label in ["By submitting my application, I acknowledge that I have read and understand Vercel's Job Applicant Privacy Notice",
                      "I understand that 1Password offers of employment are conditional",
                      "This position requires access to export controlled information. Are you a U.S. person?",
                      "Where did you first hear about this role?*",
                      "If your institution was not listed in the previous question, please enter it here.",
                      "Are you a former 1Password employee?",
                      "Are you an LLM, AI agent, or other associated agentic tool?"]:
            with self.subTest(label=label):
                self.assertIsNone(self.a(label))

    def test_forbids_tools(self):
        self.assertTrue(FORBIDS_TOOLS_RE.search(
            "I certify that I personally completed this application and that it was not filled out, in whole or in part, "
            "by another person or by an artificial intelligence (AI) tool on my behalf."))
        self.assertFalse(FORBIDS_TOOLS_RE.search(
            "We may use artificial intelligence (AI) tools to support parts of the hiring process."))


class TestPickOption(unittest.TestCase):
    def test_matching(self):
        self.assertEqual(pick_option("Austin, TX", ["Austintown, Ohio, United States", "Austin, Minnesota, United States",
                                                    "Austin, Texas, United States"]), "Austin, Texas, United States")
        self.assertEqual(pick_option("The University of Texas at Austin",
                                     ["University of Texas - Arlington", "University of Texas - Austin"]),
                         "University of Texas - Austin")
        self.assertEqual(pick_option("Decline", ["Yes", "No", "I do not want to answer"]), "I do not want to answer")
        self.assertEqual(pick_option("Yes", ["No", "Yes"]), "Yes")
        self.assertIsNone(pick_option("May 2028", ["Yes", "No"]))


class TestQueue(unittest.TestCase):
    def rec(self, **kw):
        base = {"title": "Software Engineer Intern", "company": "Acme", "locations": ["Austin, TX"],
                "terms": ["Summer 2027"], "url": "https://jobs.lever.co/acme/1", "first_seen": "2026-10-20T00:00:00"}
        return {**base, **kw}

    def test_filters(self):
        prefs = {"terms": ["Summer 2027"], "locations": ["TX"], "exclude_companies": ["Evil Corp"]}
        self.assertIsNotNone(score(self.rec(), prefs))
        self.assertIsNone(score(self.rec(terms=["Fall 2026"]), prefs))
        self.assertIsNone(score(self.rec(locations=["Seattle, WA"]), prefs))
        self.assertIsNone(score(self.rec(company="Evil Corp"), prefs))
        self.assertIsNotNone(score(self.rec(terms=[]), prefs))   # unstated term: kept, ranked lower
        self.assertGreater(score(self.rec(), prefs), score(self.rec(terms=[]), prefs))




class TestHandoff(unittest.TestCase):
    def test_route(self):
        from apply.handoff import route
        gh = "https://job-boards.greenhouse.io/vercel/jobs/1"
        wd = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/x_JR1"
        self.assertEqual(route(gh, "hybrid"), "builtin")
        self.assertEqual(route(wd, "hybrid"), "chrome")      # Jobright takes what we can't pre-fill
        self.assertEqual(route(gh, "jobright"), "chrome")
        self.assertEqual(route(wd, "builtin"), "builtin")

    def test_open_in_chrome_uses_profile(self):
        from unittest import mock
        from apply import handoff
        with mock.patch.object(handoff.subprocess, "Popen") as popen, \
             mock.patch.object(handoff.Path, "is_file", return_value=True):
            handoff.open_in_chrome("https://example.com/job", {"chrome_profile": "Profile 1"})
        args = popen.call_args[0][0]
        self.assertIn("--profile-directory=Profile 1", args)
        self.assertEqual(args[-1], "https://example.com/job")


if __name__ == "__main__":
    unittest.main()
