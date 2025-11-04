import logging
import os
import time

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

logging.basicConfig(level=logging.INFO)
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class QwenEmbed8:
    def __init__(self, model_path):
        # Load the tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        logging.info(f"Loaded tokenizer from {model_path}")

        # Load the model
        abs_path = os.path.abspath(model_path)
        optimized_path = os.path.join(abs_path, "onnx", "model_optimized.onnx")
        self.session = ort.InferenceSession(optimized_path, providers=["CPUExecutionProvider"])
        logging.info(f"Model loaded from {optimized_path}")

        # Pre-create empty KV cache tensors (reused for all requests)
        self.empty_kv_cache = {}
        for i in range(28):
            self.empty_kv_cache[f"past_key_values.{i}.key"] = np.zeros((1, 8, 0, 128), dtype=np.float32)
            self.empty_kv_cache[f"past_key_values.{i}.value"] = np.zeros((1, 8, 0, 128), dtype=np.float32)

    def embed(self, texts):
        embed_start = time.time()
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="np",
            max_length=2048,
        )

        batch_size, seq_len = inputs["input_ids"].shape

        # Prepare the basic inputs
        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
            "position_ids": np.arange(seq_len)[None, :].repeat(batch_size, axis=0).astype(np.int64),
        }

        # Reuse pre-allocated KV cache (broadcast to batch size)
        for key, tensor in self.empty_kv_cache.items():
            onnx_inputs[key] = np.broadcast_to(tensor, (batch_size, 8, 0, 128))

        # Run inference
        outputs = self.session.run(None, onnx_inputs)

        # Extract embeddings from last_hidden_state
        last_hidden_state = outputs[0]
        seq_lengths = inputs["attention_mask"].sum(axis=1) - 1
        embeddings = last_hidden_state[np.arange(batch_size), seq_lengths]

        # Normalize the embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        embed_time = time.time() - embed_start
        logging.info(f"Embedded {len(texts)} text(s) in {embed_time * 1000:.1f}ms")

        return embeddings.astype(np.float32)
