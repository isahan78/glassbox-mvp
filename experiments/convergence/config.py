"""
Experiment configuration for the mechanistic interpretability convergence experiment.

This module defines a single dataclass that holds every parameter the experiment needs:
model choice, concept definition, contrastive prompt pairs, and hyperparameters.
Keeping config separate means you can swap tasks without touching any experiment logic.
"""

import os
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ExperimentConfig:
    """All parameters for one convergence experiment run."""

    # --- Model ---
    # We use gpt2-small from the TransformerLens model zoo.
    # 12 layers, 12 heads, d_model=768. Small enough to run on CPU in minutes.
    model_name: str = "gpt2-small"
    device: str = "cpu"

    # --- Concept being studied ---
    # We're studying Indirect Object Identification (IOI):
    # "When Mary and John went to the store, John gave a drink to ___"
    # The model should predict "Mary" (the indirect object, not the subject).
    concept_name: str = "indirect_object"

    # Target token is the correct answer; foil token is the distractor.
    # GPT-2 tokenizer uses space-prefixed tokens for words mid-sentence.
    target_token: str = " Mary"
    foil_token: str = " John"

    # --- Steering ---
    # Alpha controls how strongly we push the residual stream along the
    # steering vector. Higher = more effect, but too high distorts the model.
    alpha: float = 4.0

    # --- Reproducibility ---
    seed: int = 42

    # --- Output ---
    # Use an absolute path relative to this file so outputs always land
    # in experiments/convergence/outputs/ regardless of CWD.
    output_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "outputs"
    ))

    # --- Contrastive prompt pairs ---
    # Each pair is (positive, negative). In the positive prompt, Mary is the
    # indirect object the model should predict. In the negative prompt, the
    # names are swapped so John becomes the indirect object.
    #
    # The steering vector = mean(positive activations) - mean(negative activations).
    # This isolates the direction in activation space that encodes "predict Mary
    # instead of John" — i.e., the indirect object identity direction.
    contrastive_pairs: List[Tuple[str, str]] = field(default_factory=lambda: [
        # Pattern: "When [IO] and [S] went to [place], [S] gave [object] to"
        # Positive: IO=Mary, S=John → model should say " Mary"
        # Negative: IO=John, S=Mary → model should say " John"
        (
            "When Mary and John went to the store, John gave a drink to",
            "When John and Mary went to the store, Mary gave a drink to",
        ),
        (
            "When Mary and John went to the park, John handed a ball to",
            "When John and Mary went to the park, Mary handed a ball to",
        ),
        (
            "When Mary and John went to the office, John passed a note to",
            "When John and Mary went to the office, Mary passed a note to",
        ),
        (
            "When Mary and John went to the library, John lent a book to",
            "When John and Mary went to the library, Mary lent a book to",
        ),
        (
            "When Mary and John went to the cafe, John offered a seat to",
            "When John and Mary went to the cafe, Mary offered a seat to",
        ),
        (
            "When Mary and John went to the beach, John threw a towel to",
            "When John and Mary went to the beach, Mary threw a towel to",
        ),
        (
            "When Mary and John went to the restaurant, John sent a message to",
            "When John and Mary went to the restaurant, Mary sent a message to",
        ),
        (
            "When Mary and John went to the gym, John tossed a key to",
            "When John and Mary went to the gym, Mary tossed a key to",
        ),
        (
            "When Mary and John went to the school, John gave a pencil to",
            "When John and Mary went to the school, Mary gave a pencil to",
        ),
        (
            "When Mary and John went to the mall, John showed a photo to",
            "When John and Mary went to the mall, Mary showed a photo to",
        ),
        (
            "When Mary and John went to the hospital, John brought flowers to",
            "When John and Mary went to the hospital, Mary brought flowers to",
        ),
        (
            "When Mary and John went to the station, John waved goodbye to",
            "When John and Mary went to the station, Mary waved goodbye to",
        ),
        (
            "When Mary and John went to the market, John sold a painting to",
            "When John and Mary went to the market, Mary sold a painting to",
        ),
        (
            "When Mary and John went to the airport, John handed a ticket to",
            "When John and Mary went to the airport, Mary handed a ticket to",
        ),
        (
            "When Mary and John went to the wedding, John gave a gift to",
            "When John and Mary went to the wedding, Mary gave a gift to",
        ),
    ])

    # --- Derived properties ---
    @property
    def num_pairs(self) -> int:
        return len(self.contrastive_pairs)

    @property
    def positive_prompts(self) -> List[str]:
        return [p for p, _ in self.contrastive_pairs]

    @property
    def negative_prompts(self) -> List[str]:
        return [n for _, n in self.contrastive_pairs]
