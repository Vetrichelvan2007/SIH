import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator import AgentOrchestrator
from services.document_service import process_uploaded_file
from tools.documents.document_router import route_and_process_document
from tools.images.vision_router import should_trigger_vision

class TestAgentExecutionTrace(unittest.TestCase):
    def setUp(self):
        self.scratch_dir = PROJECT_ROOT / "scratch"
        self.scratch_dir.mkdir(exist_ok=True)

    def test_01_image_workflow_context_provenance(self):
        """Test 1: Image -> Qwen VL -> context builder -> Phi-4 Mini."""
        orch = AgentOrchestrator(request_id="test_req_01")
        
        # 1. Input detection
        s_in = orch.start_step(type="input", component="input_detector", action="input_type_detection", input_summary="Uploaded screenshot.png")
        orch.complete_step(s_in, output_summary="Input Type: IMAGE")

        # 2. Image Processor
        s_img = orch.start_step(type="tool", component="image_processor", action="image_preprocessing", input_summary="Image screenshot.png")
        orch.complete_step(s_img, output_summary="Resized to 1280x720px")

        # 3. Vision Model
        s_vis = orch.start_step(type="model", component="vision", model="qwen2.5vl:3b", action="image_analysis", input_summary="Image bytes + prompt")
        vision_out = "Detected Life Analytics login screen with email input and submit button."
        orch.complete_step(s_vis, output_summary=f"Vision output: {vision_out}")
        orch.add_context_source("Qwen2.5-VL-3B", "vision_analysis", vision_out)

        # 4. Router
        s_rout = orch.start_step(type="router", component="router", model="qwen2.5:1.5b", action="route_classification", input_summary="User prompt + vision output")
        orch.complete_step(s_rout, output_summary="Route: GENERAL -> Phi-4 Mini", passed_to="Phi-4 Mini")

        # 5. Final Generation
        s_gen = orch.start_step(type="model", component="inference_engine", model="Phi-4 Mini", action="final_response_generation", input_summary="User prompt + Qwen vision analysis")
        orch.complete_step(s_gen, output_summary="Generated final user response")
        orch.set_final_generator("Phi-4 Mini", "phi4-mini", is_vision=False)

        trace = orch.build_trace()

        self.assertEqual(trace.final_generator, "Phi-4 Mini")
        self.assertFalse(trace.is_final_generator_vision)
        self.assertTrue(any(src.source == "Qwen2.5-VL-3B" for src in trace.context_sources))
        self.assertTrue(any(st.component == "vision" and st.status == "completed" for st in trace.steps))


    def test_02_direct_vision_workflow(self):
        """Test 2: Direct vision answer where Qwen VL is final generator."""
        orch = AgentOrchestrator(request_id="test_req_02")
        
        s_vis = orch.start_step(type="model", component="vision", model="qwen2.5vl:3b", action="direct_visual_qa", input_summary="What color is this image?")
        orch.complete_step(s_vis, output_summary="The image is solid red.")
        orch.set_final_generator("Qwen2.5-VL-3B", "qwen2.5vl:3b", is_vision=True)

        trace = orch.build_trace()

        self.assertEqual(trace.final_generator, "Qwen2.5-VL-3B")
        self.assertTrue(trace.is_final_generator_vision)

    def test_03_digital_pdf_no_vision_trigger(self):
        """Test 3: Digital PDF text extraction (Qwen VL omitted)."""
        pdf_path = self.scratch_dir / "sample_digital.txt"
        with open(pdf_path, "w", encoding="utf-8") as f:
            f.write("# Digital Report\nThis is pure text inside a digital document without any scanned images.")

        orch = AgentOrchestrator(request_id="test_req_03")
        res = process_uploaded_file(str(pdf_path), user_prompt="Summarize this text", filename="sample_digital.txt", orchestrator=orch)

        trace = orch.build_trace()
        vision_steps = [st for st in trace.steps if st.component == "vision"]

        self.assertEqual(len(vision_steps), 0, "Qwen VL vision model should NOT be invoked for pure digital text.")
        self.assertTrue(any(st.component == "document_router" and st.status == "completed" for st in trace.steps))

    def test_04_scanned_pdf_vision_trigger(self):
        """Test 4: Vision Router decision logic for scanned PDF / embedded images."""
        trigger, reason = should_trigger_vision(
            file_type="pdf",
            user_prompt="Read this document",
            has_scanned_pages=True,
            embedded_visual_count=0
        )
        self.assertTrue(trigger, "Scanned PDF page MUST trigger vision model.")

    def test_05_vision_failure_fallback_trace(self):
        """Test 5: Vision model failure records step failure and fallback (no false success)."""
        orch = AgentOrchestrator(request_id="test_req_05")
        
        s_vis = orch.start_step(type="model", component="vision", model="qwen2.5vl:3b", action="image_analysis", input_summary="Image bytes")
        orch.fail_step(s_vis, "Out of VRAM", fallback_action="Raw OCR text fallback")

        trace = orch.build_trace()
        failed_step = next(st for st in trace.steps if st.step_id == s_vis)

        self.assertEqual(failed_step.status, "failed")
        self.assertIn("Out of VRAM", failed_step.error)
        self.assertIn("Fallback", failed_step.output_summary)

    def test_06_multi_model_router_protection(self):
        """Test 6: Multi-model mode protection rules."""
        from services.router_service import is_router_model, can_auto_unload
        self.assertTrue(is_router_model("qwen2.5:1.5b"))

if __name__ == "__main__":
    unittest.main()
