import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.intent_classifier import classify_user_intent, TaskType
from agent.metadata_handler import handle_metadata_query
from agent.orchestrator import AgentOrchestrator

class TestUserIntentRouting(unittest.TestCase):
    def setUp(self):
        self.doc_attachment = {
            "resolved": True,
            "filename": "241801313 pandas.pdf",
            "file_type": "pdf",
            "content_type": "document",
            "page_count": 4,
            "text": "# Pandas Tutorial Code\nimport pandas as pd\ndf = pd.read_csv('data.csv')\nStudent Name: John Smith\nRoll Number: 241801313",
            "metadata": {"pages": 4}
        }
        self.img_attachment = {
            "resolved": True,
            "filename": "screenshot.png",
            "file_type": "png",
            "content_type": "visual",
            "page_count": 1,
            "text": "[Image Analysis by Qwen2.5-VL-3B]\nScreenshot of dashboard",
            "metadata": {}
        }

    def test_01_student_name_question_not_coding(self):
        """Test 1: 'What is the student name mentioned in this document?' on Python PDF MUST NOT be coding."""
        intent = classify_user_intent("What is the student name mentioned in this document?", attachment_info=self.doc_attachment)
        
        self.assertIn(intent["task_type"], [TaskType.INFORMATION_EXTRACTION.value, TaskType.DOCUMENT_QA.value])
        self.assertEqual(intent["domain"], "DOCUMENT")
        self.assertNotEqual(intent["model_id"], "qwen2.5-coder", "Student name question MUST NOT be routed to Qwen2.5-Coder!")
        self.assertEqual(intent["model_id"], "phi4-mini")

    def test_02_student_roll_number_not_coding(self):
        """Test 2: 'What is the student roll number?' MUST be information extraction, not coding."""
        intent = classify_user_intent("What is the student roll number?", attachment_info=self.doc_attachment)
        
        self.assertIn(intent["task_type"], [TaskType.INFORMATION_EXTRACTION.value, TaskType.DOCUMENT_QA.value])
        self.assertEqual(intent["domain"], "DOCUMENT")
        self.assertEqual(intent["model_id"], "phi4-mini")

    def test_03_topic_described_not_coding(self):
        """Test 3: 'What topic is described in the PDF?' MUST be document QA, not coding."""
        intent = classify_user_intent("What topic is described in the PDF?", attachment_info=self.doc_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.DOCUMENT_QA.value)
        self.assertEqual(intent["domain"], "DOCUMENT")
        self.assertEqual(intent["model_id"], "phi4-mini")

    def test_04_numpy_functions_mentioned_not_coding(self):
        """Test 4: 'What are the NumPy functions mentioned in the file?' MUST be document QA, not coding."""
        intent = classify_user_intent("What are the NumPy functions mentioned in the file?", attachment_info=self.doc_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.DOCUMENT_QA.value)
        self.assertEqual(intent["domain"], "DOCUMENT")
        self.assertEqual(intent["model_id"], "phi4-mini")

    def test_05_summarize_document_not_coding(self):
        """Test 5: 'Summarize this document.' MUST be document summarization, not coding."""
        intent = classify_user_intent("Summarize this document.", attachment_info=self.doc_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.DOCUMENT_SUMMARIZATION.value)
        self.assertEqual(intent["domain"], "DOCUMENT")
        self.assertEqual(intent["model_id"], "phi4-mini")

    def test_06_file_name_metadata_tool_no_llm(self):
        """Test 6: 'What is the file name?' MUST be metadata tool query without LLM call."""
        intent = classify_user_intent("What is the file name?", attachment_info=self.doc_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.DOCUMENT_METADATA.value)
        self.assertTrue(intent.get("is_metadata_query"))
        self.assertEqual(intent["model_id"], "metadata_tool")

        # Test direct metadata handler response
        orch = AgentOrchestrator(chat_id="meta_test_chat")
        resp = handle_metadata_query("What is the file name?", attachment_info=self.doc_attachment, orchestrator=orch)
        self.assertIn("241801313 pandas.pdf", resp)

        trace = orch.build_trace()
        self.assertEqual(trace.final_generator, "Metadata Tool (No LLM)")

    def test_07_explain_code_is_code_explanation(self):
        """Test 7: 'Explain the Python code in this document.' MUST be code explanation."""
        intent = classify_user_intent("Explain the Python code in this document.", attachment_info=self.doc_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.CODE_EXPLANATION.value)
        self.assertEqual(intent["domain"], "CODING")

    def test_08_fix_code_is_code_debugging(self):
        """Test 8: 'Fix the Python code in this document.' MUST be code debugging -> Qwen2.5-Coder."""
        intent = classify_user_intent("Fix the Python code in this document.", attachment_info=self.doc_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.CODE_DEBUGGING.value)
        self.assertEqual(intent["domain"], "CODING")
        self.assertEqual(intent["model_id"], "qwen2.5-coder")

    def test_09_write_code_is_code_generation(self):
        """Test 9: 'Write a Python program based on this document.' MUST be code generation -> Qwen2.5-Coder."""
        intent = classify_user_intent("Write a Python program based on this document.", attachment_info=self.doc_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.CODE_GENERATION.value)
        self.assertEqual(intent["domain"], "CODING")
        self.assertEqual(intent["model_id"], "qwen2.5-coder")

    def test_10_describe_image_is_vision_qa(self):
        """Test 10: 'Describe this image.' MUST be vision QA -> Qwen2.5-VL-3B."""
        intent = classify_user_intent("Describe this image.", attachment_info=self.img_attachment)
        
        self.assertEqual(intent["task_type"], TaskType.VISION_QA.value)
        self.assertEqual(intent["domain"], "VISION")
        self.assertEqual(intent["model_id"], "qwen2.5vl:3b")

if __name__ == "__main__":
    unittest.main()
