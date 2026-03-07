from typing import Dict, List, Any

class GroundTruthValidator:
    """
    Compares agent recommendations with a labeled ground-truth dataset.

    Current validation operates at the pair level:
      (original_value, proposed_token)

    Notes:
    - This does not validate file/line localization.
    - Suitable for capstone-scale token-matching accuracy evaluation.
    """
    
    def verify_accuracy(
        self,
        agent_output: List[Dict[str, Any]],
        expected_output: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Computes overlap-based evaluation against a labeled ground truth.

        Returns:
        - accuracy
        - precision
        - recall
        - f1_score
        - correct_matches
        - false_positives
        - false_negatives
        - total_expected
        - total_predicted
        """
        expected_set = {
            (item.get("original_value"), item.get("proposed_token"))
            for item in expected_output
            if item.get("original_value") is not None and item.get("proposed_token") is not None
        }

        predicted_set = {
            (item.get("original_value"), item.get("proposed_token"))
            for item in agent_output
            if item.get("original_value") is not None and item.get("proposed_token") is not None
        }

        correct_matches = len(expected_set & predicted_set)
        false_positives = len(predicted_set - expected_set)
        false_negatives = len(expected_set - predicted_set)

        total_expected = len(expected_set)
        total_predicted = len(predicted_set)

        # In this simplified validation, accuracy is treated as expected-set coverage.
        accuracy = (correct_matches / total_expected) * 100 if total_expected > 0 else 0.0
        precision = (correct_matches / total_predicted) * 100 if total_predicted > 0 else 0.0
        recall = (correct_matches / total_expected) * 100 if total_expected > 0 else 0.0

        f1_score = 0.0
        if precision + recall > 0:
            f1_score = 2 * ((precision * recall) / (precision + recall))

        return {
            "accuracy": round(accuracy, 2),
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "f1_score": round(f1_score, 2),
            "correct_matches": correct_matches,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "total_expected": total_expected,
            "total_predicted": total_predicted,
        }