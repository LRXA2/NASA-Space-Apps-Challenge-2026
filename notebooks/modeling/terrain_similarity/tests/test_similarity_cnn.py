"""Analytical contracts for the similarity experiment, not a model-quality test."""
import sys
import unittest
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from notebooks.modeling.terrain_similarity.similarity_cnn import (
    TerrainSimilarityCNN,
    context_overlap,
    contrastive_loss,
    cosine_top_k,
    rotate_batch,
    training_probabilities,
)
from notebooks.modeling.terrain_similarity.similarity_experiment import embed


class SimilarityTests(unittest.TestCase):
    def test_reflection_pooling_preserves_embedding_and_retrieval_for_all_eight_orientations(self):
        torch.manual_seed(35)
        torch.set_num_threads(2)
        model = TerrainSimilarityCNN()
        values = np.random.default_rng(35).normal(size=(4, 3, 32, 32)).astype(np.float32)
        original = embed(model, values, torch.device('cpu'), include_reflections=True)
        # Independently form the square's symmetries with NumPy; only spatial
        # axes move. This fails if reflections are omitted or channels are flipped.
        for mirrored in (False, True):
            for turns in range(4):
                changed = np.flip(values, axis=-1) if mirrored else values
                changed = np.rot90(changed, turns, axes=(-2, -1)).copy()
                actual = embed(model, changed, torch.device('cpu'), include_reflections=True)
                with self.subTest(mirrored=mirrored, turns=turns):
                    np.testing.assert_allclose(actual, original, rtol=0, atol=1e-6)
                    order, _ = cosine_top_k(actual[0], original, ['a', 'b', 'c', 'd'], 4)
                    expected_order, _ = cosine_top_k(original[0], original, ['a', 'b', 'c', 'd'], 4)
                    np.testing.assert_array_equal(order, expected_order)

    def test_cosine_ranking_is_bidirectional_and_ties_use_ids(self):
        order, scores = cosine_top_k(np.array([1., 0.]), np.array([[0., 1.], [2., 0.], [1., 0.]]), ['z', 'b', 'a'], 3)
        np.testing.assert_array_equal(order, [2, 1, 0])
        np.testing.assert_allclose(scores, [1., 1., 0.])
        _, forward = cosine_top_k(np.array([1., 1.]), np.array([[1., 0.]]), ['earth'])
        _, reverse = cosine_top_k(np.array([1., 0.]), np.array([[1., 1.]]), ['moon'])
        np.testing.assert_allclose(forward, [1/np.sqrt(2)])
        np.testing.assert_allclose(forward, reverse)

    def test_overlapping_neighbor_is_not_a_false_negative_in_loss(self):
        values = torch.tensor([[1., 0.], [1., 0.], [0., 1.]])
        blocked = torch.tensor([[1, 1, 0], [1, 1, 0], [0, 0, 1]], dtype=torch.bool)
        expected = (2 * np.log1p(2 * np.exp(-2)) + np.log1p(4 * np.exp(-2))) / 3
        self.assertAlmostEqual(float(contrastive_loss(values, values, blocked, .5)), expected, places=6)

    def test_sampling_excludes_holdout_and_balances_regions(self):
        roles, regions = ['train', 'train', 'train', 'holdout'], ['a', 'a', 'b', 'c']
        indices, weights = training_probabilities(roles, regions, 'region_balanced')
        np.testing.assert_array_equal(indices, [0, 1, 2])
        np.testing.assert_allclose(weights, [.25, .25, .5])
        _, uniform = training_probabilities(roles, regions, 'count_weighted')
        np.testing.assert_allclose(uniform, [1/3, 1/3, 1/3])
        with self.assertRaises(ValueError):
            training_probabilities(roles, ['a', 'a', 'b', 'a'], 'region_balanced')

    def test_contrastive_loss_matches_two_orthogonal_pairs(self):
        # Each anchor has one positive of cosine 1 and two negatives of cosine 0.
        values = torch.eye(2, requires_grad=True)
        loss = contrastive_loss(values, values, torch.eye(2, dtype=torch.bool), temperature=.5)
        self.assertAlmostEqual(float(loss.detach()), float(np.log1p(2 * np.exp(-2))), places=6)
        loss.backward()
        assert values.grad is not None
        self.assertTrue(torch.isfinite(values.grad).all())
        with self.assertRaises(ValueError):
            contrastive_loss(values, values, torch.ones((2, 2), dtype=torch.bool))

    def test_negative_mask_excludes_touching_context_and_duplicate_locations(self):
        bounds = np.array([[0., 0., 10., 10.], [10., 0., 20., 10.], [30., 0., 40., 10.], [0., 0., 10., 10.]])
        result = context_overlap(bounds, np.array(['moon', 'moon', 'moon', 'earth']))
        np.testing.assert_array_equal(result, [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    def test_rotation_preserves_channel_alignment_and_physical_amplitude(self):
        values = torch.tensor([[[[1., 2.], [3., 4.]], [[11., 12.], [13., 14.]], [[21., 22.], [23., 24.]]]])
        rotated = rotate_batch(values, np.array([1]))
        np.testing.assert_array_equal(rotated[0, 0].numpy(), [[2., 4.], [1., 3.]])
        np.testing.assert_array_equal((rotated[0, 1] - rotated[0, 0]).numpy(), [[10., 10.], [10., 10.]])


if __name__ == '__main__':
    unittest.main()
