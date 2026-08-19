import os
import time
import threading
from typing import Optional, Tuple, Any
import numpy as np
from PIL import Image

# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


class DINOExtractor:
    """
    Feature Extractor for REMIND Visual Memory.
    Loads DINOv3 (via Hugging Face Transformers) with automatic fallback to DINOv2 / CPU-optimized mode.
    Extracts L2-normalized global embedding vectors for cosine similarity novelty indexing.
    """

    DEFAULT_DINOV3_MODEL = "facebook/dinov3-vits16-pretrain-lvd1689m"
    FALLBACK_DINOV2_MODEL = "dinov2_vits14"

    def __init__(
        self,
        model_name: Optional[str] = None,
        use_mock_if_unavailable: bool = True,
        lazy_init: bool = True,
    ):
        self.model_name = model_name or self.DEFAULT_DINOV3_MODEL
        self.use_mock_if_unavailable = use_mock_if_unavailable
        self._lock = threading.Lock()
        self.model = None
        self.processor = None
        self.is_mock = False
        self.embedding_dim = 384
        self._initialized = False

        if not lazy_init:
            self._init_model()

    def _init_model(self):
        if self._initialized:
            return
        self._initialized = True

        # Check if offline mode is requested
        if os.environ.get("DINO_OFFLINE") == "1":
            print(f"{YELLOW}[DINO] DINO_OFFLINE requested -> Running fast local feature engine.{RESET}")
            self.is_mock = True
            return

        # 1. Attempt Hugging Face Transformers DINOv3
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env")))
            load_dotenv()

            hf_token = (
                os.environ.get("HF_TOKEN")
                or os.environ.get("HUGGINGFACE_TOKEN")
                or os.environ.get("HUGGING_FACE_HUB_TOKEN")
                or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
                or os.environ.get("HUGGING_FACE_TOKEN")
            )
            if hf_token:
                os.environ["HF_TOKEN"] = hf_token

            print(f"{BLUE}[DINO] Attempting to load DINOv3 from Hugging Face ({self.model_name})...{RESET}")
            from transformers import AutoImageProcessor, AutoModel
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.processor = AutoImageProcessor.from_pretrained(
                self.model_name,
                local_files_only=False,
                token=hf_token,
            )
            self.model = AutoModel.from_pretrained(
                self.model_name,
                device_map="auto" if torch.cuda.is_available() else None,
                local_files_only=False,
                token=hf_token,
            )
            if not torch.cuda.is_available():
                self.model = self.model.to("cpu")
            self.model.eval()
            print(f"{GREEN}[DINO] DINOv3 loaded successfully on {self.device}!{RESET}")
            return
        except Exception as e3:
            print(f"{YELLOW}[DINO] Hugging Face DINOv3 unavailable ({e3}). Checking local TorchHub DINOv2...{RESET}")

        # 2. Fallback to TorchHub DINOv2
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = torch.hub.load("facebookresearch/dinov2", self.FALLBACK_DINOV2_MODEL)
            self.model.eval().to(self.device)
            import torchvision.transforms as T
            self.transform = T.Compose([
                T.Resize((224, 224)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            print(f"{GREEN}[DINO] DINOv2 ({self.FALLBACK_DINOV2_MODEL}) loaded successfully on {self.device}!{RESET}")
            return
        except Exception as e2:
            print(f"{YELLOW}[DINO] TorchHub DINOv2 unavailable ({e2}).{RESET}")

        # 3. Simulation / Lightweight Fallback mode
        if self.use_mock_if_unavailable:
            print(f"{YELLOW}[DINO] Running in lightweight color-histogram feature extraction mode.{RESET}")
            self.is_mock = True
        else:
            raise RuntimeError("Could not initialize DINO model.")

    def extract_features(self, pil_image: Image.Image) -> np.ndarray:
        """
        Extracts an L2-normalized 384-dimensional feature vector from a PIL Image.
        Thread-safe.
        """
        if not self._initialized:
            self._init_model()

        with self._lock:
            if self.is_mock:
                return self._extract_fallback_features(pil_image)

            try:
                import torch
                if self.processor is not None:
                    # Hugging Face Transformers pipeline
                    inputs = self.processor(images=pil_image, return_tensors="pt")
                    if hasattr(self, "device") and self.device == "cuda":
                        inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        if hasattr(outputs, "last_hidden_state"):
                            feat = outputs.last_hidden_state.mean(dim=1)
                        elif hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
                            feat = outputs.pooler_output
                        else:
                            feat = outputs[0].mean(dim=1)

                        feat_norm = torch.nn.functional.normalize(feat, p=2, dim=-1)
                        return feat_norm.squeeze(0).cpu().numpy().astype(np.float32)
                else:
                    # TorchHub DINOv2 pipeline
                    tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
                    with torch.no_grad():
                        patch_tokens = self.model.get_intermediate_layers(tensor, n=1)[0].squeeze(0)
                        patch_tokens_norm = torch.nn.functional.normalize(patch_tokens, p=2, dim=1)
                        global_feat = patch_tokens_norm.mean(dim=0, keepdim=True)
                        global_feat_norm = torch.nn.functional.normalize(global_feat, p=2, dim=1)
                        return global_feat_norm.squeeze(0).cpu().numpy().astype(np.float32)

            except Exception as e:
                print(f"{RED}[DINO Extraction Error] {e}. Falling back to color descriptor.{RESET}")
                return self._extract_fallback_features(pil_image)

    def _extract_fallback_features(self, pil_image: Image.Image) -> np.ndarray:
        """Fast, deterministic image feature vector (384-D) based on spatial color histograms."""
        resized = pil_image.resize((32, 32)).convert("RGB")
        arr = np.array(resized, dtype=np.float32) / 255.0

        # Create spatial block histograms (4x4 blocks = 16 blocks * 24 color bins = 384-D)
        feats = []
        for r in range(4):
            for c in range(4):
                block = arr[r*8:(r+1)*8, c*8:(c+1)*8]
                # 8 bins per R, G, B
                hist_r, _ = np.histogram(block[:, :, 0], bins=8, range=(0.0, 1.0))
                hist_g, _ = np.histogram(block[:, :, 1], bins=8, range=(0.0, 1.0))
                hist_b, _ = np.histogram(block[:, :, 2], bins=8, range=(0.0, 1.0))
                feats.extend(hist_r)
                feats.extend(hist_g)
                feats.extend(hist_b)

        vec = np.array(feats, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec
