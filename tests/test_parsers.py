"""Offline parser tests. Fixtures are trimmed copies of real responses seen on 2026-10-22."""
import unittest
from unittest import mock

from scraper import jsonld
from scraper.ats import icims, jazzhr
from scraper.registry import board_from_url
from scraper.scorecard import job_key

ICIMS_PAGE = """
<li class="iCIMS_JobCardItem">
<div class="row">
<div class="col-xs-6 header left">
<span class="sr-only field-label">Location</span>
<span >
US-VA-Lynchburg</span>
</div>
<div class="col-xs-12 title">
<a href="https://careers-framatome.icims.com/jobs/3294/%28computer-science-engineering%29-intern/job?in_iframe=1" class="iCIMS_Anchor" title="3294 - (Computer Science Engineering) Intern - Univ/Co-Op Technical (Lynchburg, VA)">
<h3 >(Computer Science Engineering) Intern</h3></a>
</div>
<dt class="iCIMS_JobHeaderField">Category</dt>
<dd class="iCIMS_JobHeaderData"><span >
Engineering, Intern/Co-op</span>
</dd>
</div>
</li>
"""

JAZZ_FEED = """<jobs><job>
<id><![CDATA[job_1]]></id><status><![CDATA[Open]]></status>
<title><![CDATA[Backend Developer Intern]]></title>
<url><![CDATA[https://acme.applytojob.com/apply/AbC123xyZ9/Backend-Developer-Intern]]></url>
<city><![CDATA[Arlington]]></city><state><![CDATA[VA]]></state><country><![CDATA[United States]]></country>
<type><![CDATA[Intern]]></type><description><![CDATA[<p>Python and APIs</p>]]></description>
</job><job>
<id><![CDATA[job_2]]></id><status><![CDATA[Closed]]></status><title><![CDATA[Old]]></title>
<url><![CDATA[https://acme.applytojob.com/apply/Zzz/Old]]></url>
</job></jobs>"""

LD_PAGE = """<script type="application/ld+json">{"@type": "JobPosting", "title": "SWE Intern",
"datePosted": "2026-10-01T00:00:00Z", "description": "&lt;p&gt;Write Go&lt;/p&gt;",
"jobLocation": [{"@type": "Place", "address": {"addressLocality": "Portsmouth", "addressRegion": "NH",
"addressCountry": "US", "postalCode": "UNAVAILABLE"}}]}</script>"""


class TestParsers(unittest.TestCase):
    def test_icims_cards(self):
        with mock.patch.object(icims, "get_text", side_effect=[ICIMS_PAGE, None]):
            jobs = icims.fetch({"host": "careers-framatome.icims.com"})
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["job_id"], "3294")
        self.assertEqual(j["locations"], ["US-VA-Lynchburg"])
        self.assertTrue(j["_intern_type"])
        self.assertTrue(j["title"].startswith("(Computer Science Engineering) Intern"))

    def test_jazzhr_feed(self):
        with mock.patch.object(jazzhr, "get_text", return_value=JAZZ_FEED):
            jobs = jazzhr.fetch({"company": "acme"})
        self.assertEqual([j["job_id"] for j in jobs], ["AbC123xyZ9"])  # closed job skipped
        self.assertEqual(jobs[0]["locations"], ["Arlington, VA, United States"])
        self.assertTrue(jobs[0]["_intern_type"])

    def test_jsonld(self):
        info = jsonld.job_posting(LD_PAGE)
        self.assertEqual(info["locations"], ["Portsmouth, NH, US"])
        self.assertEqual(info["posted_at"], "2026-10-01")
        self.assertIn("Write Go", info["description"])

    def test_registry_and_keys_agree(self):
        cases = {
            "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/SWE-Intern_JR1":
                ("workday", "wd:nvidia:swe-intern_jr1"),
            "https://job-boards.eu.greenhouse.io/axiomaticai/jobs/4848121101": ("greenhouse", "gh:4848121101"),
            "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_45001/job/334325":
                ("oracle", "eeho.fa.us2.oraclecloud.com:334325"),
            "https://jobs.grainger.com/job/CHICAGO-GTG-Intern-Software-Engineer-IL-60661-4555/1419930800/?ats=successfactors":
                ("successfactors", "jobs.grainger.com:1419930800"),
        }
        for url, (ats, key) in cases.items():
            with self.subTest(url=url):
                self.assertEqual(board_from_url(url)[0], ats)
                self.assertEqual(job_key(url), key)


if __name__ == "__main__":
    unittest.main()
