"""
YOLOv5 Detection Tool for CrewAI
Wraps the existing yolov5/detect.py into a CrewAI BaseTool
"""
import os
import sys
import json
import glob
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Add project root to path so wasteDetection package is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class YOLOv5InputSchema(BaseModel):
    image_path: str = Field(
        ...,
        description="Path to the image file for waste detection (e.g. 'data/inputImage.jpg')"
    )


class YOLOv5DetectionTool(BaseTool):
    name: str = "Waste Detection Tool"
    description: str = (
        "Detects waste in an image using YOLOv5. "
        "Input: the image file path as a plain string (e.g. data/inputImage.jpg). "
        "Returns JSON with: waste_detected, num_detections, detections, message."
    )
    args_schema: Type[BaseModel] = YOLOv5InputSchema

    def _run(self, image_path: str = "", **kwargs) -> str:
        # Handle both string and dict inputs from crewai's ReAct agent
        if isinstance(image_path, dict):
            image_path = image_path.get("image_path", "data/inputImage.jpg")
        if not image_path:
            image_path = "data/inputImage.jpg"

        try:
            # Clean any previous detection runs
            if os.path.exists("yolov5/runs"):
                os.system("rm -rf yolov5/runs")

            # Check model weights
            weights = "yolov5/my_model.pt"
            if not os.path.exists(weights):
                weights = "yolov5s.pt"   # fallback for demo if custom weights missing

            # Run YOLOv5 detection
            cmd = (
                f"cd yolov5/ && python detect.py "
                f"--weights {os.path.basename(weights)} "
                f"--img 416 --conf 0.5 "
                f"--source ../{image_path} "
                f"--save-txt --save-conf 2>&1"
            )
            os.system(cmd)

            # Find latest output directory
            output_dirs = sorted(glob.glob("yolov5/runs/detect/exp*"))
            if not output_dirs:
                return json.dumps({
                    "waste_detected": False,
                    "num_detections": 0,
                    "detections": [],
                    "output_image_path": None,
                    "message": "No detections found or model output missing."
                })

            latest_dir = output_dirs[-1]

            # Parse label files for class IDs and confidence scores
            detections = []
            label_files = glob.glob(f"{latest_dir}/labels/*.txt")
            if label_files:
                with open(label_files[0], "r") as f:
                    for line in f.readlines():
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            confidence = float(parts[5]) if len(parts) > 5 else 0.75
                            detections.append({
                                "class_id": class_id,
                                "confidence": round(confidence, 2)
                            })

            # Find the annotated output image
            output_images = (
                glob.glob(f"{latest_dir}/*.jpg") +
                glob.glob(f"{latest_dir}/*.png") +
                glob.glob(f"{latest_dir}/*.jpeg")
            )
            output_image_path = output_images[0] if output_images else None

            result = {
                "waste_detected": len(detections) > 0,
                "num_detections": len(detections),
                "detections": detections,
                "output_image_path": output_image_path,
                "message": (
                    f"Found {len(detections)} waste item(s) in the image."
                    if detections else "No waste detected in this image."
                )
            }
            return json.dumps(result)

        except Exception as e:
            return json.dumps({
                "waste_detected": False,
                "num_detections": 0,
                "detections": [],
                "output_image_path": None,
                "message": f"Detection error: {str(e)}"
            })
