import hashlib
import random
from typing import List

def get_text_embedding(text: str) -> List[float]:
    """
    Generates a deterministic 768-dimensional vector embedding based on the hash of the text.
    Ensures reproducibility and works 100% offline without downloading models.
    """
    if not text:
        return [0.0] * 768
        
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    random.seed(int(h, 16))
    return [random.uniform(-1.0, 1.0) for _ in range(768)]
