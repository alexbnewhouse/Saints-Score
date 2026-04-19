"""Tests for saints_score.semantic.convergence — similarity and entropy."""

import numpy as np

from saints_score.semantic.convergence import compute_similarity, compute_unigram_entropy


def test_compute_similarity_identical_vectors():
    """Identical normalized vectors should have similarity ~1.0."""
    v = np.array([1.0, 0.0, 0.0])
    embeddings = np.tile(v, (10, 1))
    stats = compute_similarity(embeddings)
    assert abs(stats["median"] - 1.0) < 1e-6
    assert stats["n"] == 10


def test_compute_similarity_single_vector():
    """Single vector should return zero stats."""
    embeddings = np.array([[1.0, 0.0, 0.0]])
    stats = compute_similarity(embeddings)
    assert stats["median"] == 0.0
    assert stats["n"] == 1


def test_compute_similarity_orthogonal():
    """Orthogonal normalized vectors should have similarity ~0."""
    embeddings = np.eye(5)  # 5 orthogonal unit vectors
    stats = compute_similarity(embeddings)
    assert abs(stats["median"]) < 1e-6


def test_compute_unigram_entropy_uniform():
    """Entropy should be higher for diverse text."""
    diverse = ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]
    repetitive = ["hello hello hello", "hello hello hello", "hello hello hello"]

    h_diverse = compute_unigram_entropy(diverse)
    h_repetitive = compute_unigram_entropy(repetitive)

    assert h_diverse > h_repetitive


def test_compute_unigram_entropy_empty():
    assert compute_unigram_entropy([]) == 0.0
    assert compute_unigram_entropy([""]) == 0.0
