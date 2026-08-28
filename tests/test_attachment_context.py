import os
import sys
import unittest
import uuid
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator import AgentOrchestrator
from agent.state import register_attachment, get_chat_attachments, delete_attachment
from agent.context_manager import resolve_attachment_context, build_unified_context, is_document_grounded_query

class TestAttachmentContextAndState(unittest.TestCase):
    def setUp(self):
        self.chat_id = f"test_chat_{uuid.uuid4().hex[:8]}"

    def test_01_initial_document_upload_and_context(self):
        """Test 1: Initial document upload registers attachment state."""
        file_data = {
            "file_type": "pdf",
            "content_type": "document",
            "filename": "241801309 numpy.pdf",
            "text": "Header: NumPy Python Library Report\nAuthor: Dr. Alex Mercer\nNumPy array operations and functions.",
            "metadata": {"pages": 3}
        }
        
        orch = AgentOrchestrator(chat_id=self.chat_id)
        res = resolve_attachment_context(
            chat_id=self.chat_id,
            user_query="describe this document",
            current_file_data=file_data,
            orchestrator=orch
        )

        self.assertTrue(res["resolved"])
        self.assertTrue(res["is_new"])
        self.assertEqual(res["filename"], "241801309 numpy.pdf")

        # Verify persisted in SQLite
        attachments = get_chat_attachments(self.chat_id)
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["filename"], "241801309 numpy.pdf")

    def test_02_follow_up_query_without_reuploading(self):
        """Test 2: Follow-up query retrieves persistent attachment context without re-uploading file."""
        # Pre-register attachment
        file_data = {
            "file_type": "pdf",
            "content_type": "document",
            "filename": "241801309 numpy.pdf",
            "text": "Author: Dr. Alex Mercer\nFunctions: np.array(), np.dot(), np.zeros()",
            "metadata": {"pages": 2}
        }
        register_attachment(self.chat_id, "241801309 numpy.pdf", "pdf", "document", file_data)

        # User asks text-only follow-up question
        orch = AgentOrchestrator(chat_id=self.chat_id)
        res = resolve_attachment_context(
            chat_id=self.chat_id,
            user_query="what are the numpy functions?",
            current_file_data=None,
            orchestrator=orch
        )

        self.assertTrue(res["resolved"], "Follow-up question MUST resolve conversation attachment.")
        self.assertFalse(res["is_new"])
        self.assertEqual(res["filename"], "241801309 numpy.pdf")
        self.assertIn("np.array()", res["text"])

        # Build unified prompt context
        prompt = build_unified_context("what are the numpy functions?", res, orchestrator=orch)
        self.assertIn("np.array()", prompt)

        # Check trace orchestrator context sources
        trace = orch.build_trace()
        sources = [src.source for src in trace.context_sources]
        types = [src.type for src in trace.context_sources]

        self.assertIn("attachment_resolver", sources)
        self.assertIn("attached_file_context", types)


    def test_03_name_extraction_grounding(self):
        """Test 3: Name extraction query resolves document context."""
        file_data = {
            "file_type": "pdf",
            "content_type": "document",
            "filename": "241801309 numpy.pdf",
            "text": "Document Title: Advanced Array Computing\nLead Researcher: Prof. Sarah Jenkins\nInstitution: MIT",
            "metadata": {"pages": 1}
        }
        register_attachment(self.chat_id, "241801309 numpy.pdf", "pdf", "document", file_data)

        orch = AgentOrchestrator(chat_id=self.chat_id)
        res = resolve_attachment_context(
            chat_id=self.chat_id,
            user_query="who's name is mention in the pdf",
            current_file_data=None,
            orchestrator=orch
        )

        self.assertTrue(res["resolved"])
        prompt = build_unified_context("who's name is mention in the pdf", res, orchestrator=orch)
        self.assertIn("Prof. Sarah Jenkins", prompt)

    def test_04_missing_attachment_hallucination_guard(self):
        """Test 4: Missing attachment triggers Hallucination Prevention Guard notice."""
        fresh_chat_id = f"fresh_chat_{uuid.uuid4().hex[:8]}"

        orch = AgentOrchestrator(chat_id=fresh_chat_id)
        res = resolve_attachment_context(
            chat_id=fresh_chat_id,
            user_query="who's name is mentioned in the pdf?",
            current_file_data=None,
            orchestrator=orch
        )

        self.assertFalse(res["resolved"])
        self.assertTrue(res["is_grounded_query"])
        self.assertEqual(res["reason"], "missing_attachment")
        self.assertIn("Please upload or attach the file", res["notice_response"])

        # Check trace records failure step in hallucination guard
        trace = orch.build_trace()
        failed_steps = [st for st in trace.steps if st.status == "failed"]
        self.assertTrue(any(st.component == "hallucination_guard" for st in failed_steps))

    def test_05_image_follow_up_vision_analysis_retrieval(self):
        """Test 5: Image follow-up question retrieves stored Qwen2.5-VL-3B vision analysis."""
        img_data = {
            "file_type": "image",
            "content_type": "visual",
            "filename": "certificate.png",
            "text": "[Image Analysis by Qwen2.5-VL-3B]\nCertificate of Excellence awarded to Johnathan Doe.",
            "visual_content": [{"page": 1, "type": "direct_image", "analysis": "Certificate awarded to Johnathan Doe"}],
            "analysis": "Certificate awarded to Johnathan Doe"
        }
        register_attachment(self.chat_id, "certificate.png", "image", "visual", img_data)

        orch = AgentOrchestrator(chat_id=self.chat_id)
        res = resolve_attachment_context(
            chat_id=self.chat_id,
            user_query="what is the name shown on the certificate?",
            current_file_data=None,
            orchestrator=orch
        )

        self.assertTrue(res["resolved"])
        self.assertEqual(res["filename"], "certificate.png")
        self.assertIn("Johnathan Doe", res["text"])

    def test_06_multiple_attachments_resolution(self):
        """Test 6: Resolving target attachment when multiple files are attached to session."""
        att_a = {
            "file_type": "pdf",
            "content_type": "document",
            "filename": "A.pdf",
            "text": "Content of Document A: Financial Q3 Report",
            "metadata": {"pages": 1}
        }
        att_b = {
            "file_type": "pdf",
            "content_type": "document",
            "filename": "B.pdf",
            "text": "Content of Document B: Technical Architecture Specs",
            "metadata": {"pages": 1}
        }

        register_attachment(self.chat_id, "A.pdf", "pdf", "document", att_a)
        register_attachment(self.chat_id, "B.pdf", "pdf", "document", att_b)

        # Ask specifically about B.pdf
        orch = AgentOrchestrator(chat_id=self.chat_id)
        res = resolve_attachment_context(
            chat_id=self.chat_id,
            user_query="what is mentioned in B.pdf?",
            current_file_data=None,
            orchestrator=orch
        )

        self.assertTrue(res["resolved"])
        self.assertEqual(res["filename"], "B.pdf")
        self.assertIn("Technical Architecture Specs", res["text"])

if __name__ == "__main__":
    unittest.main()
