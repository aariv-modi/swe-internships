"""Cases come from real postings seen while measuring the existing lists (2026-10-22)."""
import unittest

from scraper.classify import (description_is_swe, is_internship, is_swe, location_is_us,
                              swe_verdict, terms, us_status)


class TestSWE(unittest.TestCase):
    YES = [
        "2027 Software Engineering Summer Internship",
        "Software Engineering Intern (Summer 2027)",
        "GNC Software Engineering Intern (Summer 2027)",
        "Flight Software & GNC Intern - Spring/Summer 2027",
        "Platform & Site Reliability Engineering Internship - Summer 2027",
        "Android Developer Intern, 2027",
        "Developer Internship",
        "Embedded Software Engineer Intern, Implant Embedded Systems",
        "Software Development Engineer in Test Intern",
        "Python Developer Intern",
        "DevOps Engineer Intern - Summer 2027",
        "Infrastructure Engineer Intern",
        "Forward Deployed Software Engineer, Internship - US Government",
        "Quantitative Developer Intern",
        "Machine Learning Engineer Intern",
        "Full-Stack Engineering Intern - Summer 2027",
        "AI Software Intern - Cloud, Infrastructure & Data Centre Deployment",
    ]
    NO = [
        "Water Infrastructure Engineering Intern",
        "Platform Solutions Engineer Intern (EE)",
        "Developer Community Engagement Intern",
        "Mechanical Engineer Intern (Summer 2027)",
        "Data Analyst, Intern",
        "PhD Data Scientist, Intern",
        "Business Development Intern",
        "Marketing & Revenue Operations Intern",
        "Research Associate Intern",
        "Quantitative Trader Intern",
        "Product Manager Intern",
        "Information Technology Intern",
        "Electrical Engineer Intern",
    ]

    def test_yes(self):
        for t in self.YES:
            with self.subTest(t=t):
                self.assertTrue(is_swe(t) and is_internship(t))

    def test_no(self):
        for t in self.NO:
            with self.subTest(t=t):
                self.assertFalse(is_swe(t))

    def test_internship(self):
        self.assertFalse(is_internship("Internal Tools Software Engineer"))
        self.assertFalse(is_internship("High School Internship, Software Engineering (Summer 2027)"))
        self.assertTrue(is_internship("Winter Co-op 2027 - Software Engineering"))


class TestVerdict(unittest.TestCase):
    def test_maybe(self):
        for t in ["Engineer (Intern)", "Robotics Engineer Intern", "Technology Intern",
                  "Summer 2027 Internship - Member of Technical Staff - Agent Systems"]:
            with self.subTest(t=t):
                self.assertEqual(swe_verdict(t), "maybe")

    def test_exact_beats_function_words(self):
        self.assertEqual(swe_verdict("Software Engineering Intern - Technology Analyst"), "yes")
        self.assertEqual(swe_verdict("Application Development Intern"), "yes")
        self.assertEqual(swe_verdict("Forward Deployed Engineer Intern"), "yes")
        self.assertEqual(swe_verdict("Wind Development Intern"), "no")
        self.assertEqual(swe_verdict("Project Engineer Intern - Summer 2027"), "no")

    def test_typed_intern(self):
        self.assertTrue(is_internship("Software Engineer", typed_intern=True))
        self.assertFalse(is_internship("Software Engineer"))

    def test_description(self):
        sw = ("You will write production code in Python and TypeScript, build REST APIs, "
              "deploy on AWS with Docker, and review pull requests in Git.")
        hw = ("Design brackets in SolidWorks, run thermal analysis in ANSYS, produce CAD drawings "
              "with GD&T and support machining and fabrication. Some Python scripting.")
        it = "Help desk ticketing, troubleshooting laptops, imaging, Active Directory, some SQL."
        self.assertTrue(description_is_swe(sw))
        self.assertFalse(description_is_swe(hw))
        self.assertFalse(description_is_swe(it))


class TestLocation(unittest.TestCase):
    def test_us(self):
        for loc in ["Austin, Texas, United States", "Westminster, CO", "US-CA-San Jose",
                    "San Francisco", "New York", "Remote, United States", "Las Cruces, New Mexico",
                    "Santa Clara CA 95054", "Remote", "Cambridge, MA", "Chicago Office"]:
            with self.subTest(loc=loc):
                self.assertTrue(location_is_us(loc))

    def test_not_us(self):
        for loc in ["Toronto, CA", "Frankfurt, DE", "Colombia, Remote", "Markham, Ontario, Canada",
                    "Onsite in Bangalore", "Lausanne  Switzerland", "London", "Munich",
                    "Mexico City, Mexico"]:
            with self.subTest(loc=loc):
                self.assertFalse(location_is_us(loc))

    def test_unknown(self):
        self.assertIsNone(location_is_us("2 Locations"))
        self.assertIsNone(us_status(["Headquarters"]))
        self.assertTrue(us_status(["London", "Seattle, WA"]))


class TestTerms(unittest.TestCase):
    def test_terms(self):
        self.assertEqual(terms("Software Engineering Intern (Summer 2027)"), ["Summer 2027"])
        self.assertEqual(terms("2027 Software Engineering Summer Internship"), ["Summer 2027"])
        self.assertEqual(terms("Flight Software & GNC Intern - Spring/Summer 2027"),
                         ["Spring 2027", "Summer 2027"])
        self.assertEqual(terms("Software Engineering Intern - Connected Systems (January - August 2027)"),
                         ["Winter 2027"])
        self.assertEqual(terms("Fall '26 SWE Intern"), ["Fall 2026"])
        self.assertEqual(terms("Software Engineer Intern"), [])


if __name__ == "__main__":
    unittest.main()
