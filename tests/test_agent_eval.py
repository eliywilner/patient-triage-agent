"""Automated Agent Evaluation Suite & Regression Test Harness.

Tests red flag classification accuracy, routine symptom care auto-triaging,
PII redaction guardrails, structured JSON logging, and system constitution compliance.
"""

import unittest
import json
import logging
from app.agent import (
    agent,
    parse_and_triage_symptoms,
    evaluate_guardrails,
    PatientSymptomReport,
    VitalSigns,
    SYSTEM_CONSTITUTION,
)
from app.observability import PIIRedactor, JSONFormatter


class TestAgentEvaluation(unittest.TestCase):
    """Automated test harness evaluating Agent capabilities and compliance."""

    def test_system_constitution_defined(self):
        """Verify that system constitution is explicitly defined with triage guidelines."""
        self.assertIsNotNone(SYSTEM_CONSTITUTION)
        self.assertIn("Patient Safety First", SYSTEM_CONSTITUTION)
        self.assertIn("Human-in-the-Loop Interrupt", SYSTEM_CONSTITUTION)

    def test_red_flag_symptom_triage(self):
        """Verify that high fever and chest pain trigger urgent physician review node."""
        msg = "Patient Jane Doe, 35yo, reports severe acute chest pain and high fever of 103.2 F."
        res = agent.query(message=msg, session_id="test-urgent-session")

        self.assertIsNotNone(res)
        report = res.get("patient_report") or res.get("payload", {}).get("patient_report", {})
        self.assertIsNotNone(report)
        self.assertTrue(report.get("is_urgent"))
        self.assertGreater(len(report.get("red_flags", [])), 0)

    def test_routine_symptom_triage(self):
        """Verify that normal vitals without red flags automatically route to routine care."""
        msg = "Patient reports mild seasonal allergy congestion. Temp 98.6 F, SpO2 99%."
        res = agent.query(message=msg, session_id="test-routine-session")

        self.assertIsNotNone(res)
        self.assertEqual(res.get("status"), "TRIAGE_COMPLETE")
        decision = res.get("triage_decision", {})
        self.assertEqual(decision.get("urgency_level"), "LOW")
        self.assertEqual(decision.get("action"), "AUTOMATED_ROUTINE")

    def test_pii_redaction_guardrail(self):
        """Verify that PII redactor removes SSN, phone number, and email patterns."""
        redactor = PIIRedactor()
        raw_text = "Patient SSN is 123-45-6789, phone is 555-123-4567, email is patient@example.com."
        clean_text = redactor.redact(raw_text)

        self.assertNotIn("123-45-6789", clean_text)
        self.assertNotIn("555-123-4567", clean_text)
        self.assertNotIn("patient@example.com", clean_text)
        self.assertIn("[REDACTED_SSN]", clean_text)
        self.assertIn("[REDACTED_PHONE]", clean_text)
        self.assertIn("[REDACTED_EMAIL]", clean_text)

    def test_structured_json_formatter(self):
        """Verify that JSONFormatter outputs valid structured JSON log records."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test log message",
            args=(),
            exc_info=None,
        )
        record.intent = "Check symptom"
        record.outcome = "Routine care"
        record.session_id = "test-session-1"

        formatted_json = formatter.format(record)
        parsed = json.loads(formatted_json)

        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["message"], "Test log message")
        self.assertEqual(parsed["intent"], "Check symptom")
        self.assertEqual(parsed["outcome"], "Routine care")
        self.assertEqual(parsed["session_id"], "test-session-1")


if __name__ == "__main__":
    unittest.main()

