from typing import Dict, List

class GroundTruthValidator:
    """
    Compares agent recommendations with a labeled ground-truth dataset.
    """

    def verify_accuracy(
        self,
        agent_output: List[Dict],
        expected_output: List[Dict],
    ) -> Dict:

        expected_set = {
            (item["original_value"], item["proposed_token"])
            for item in expected_output
        }

        correct_matches = 0

        for rec in agent_output:

            pair = (rec.get("original_value"), rec.get("proposed_token"))

            if pair in expected_set:
                correct_matches += 1

        total_expected = len(expected_output)

        accuracy = (
            (correct_matches / total_expected) * 100
            if total_expected > 0
            else 0
        )

        return {
            "accuracy": round(accuracy, 2),
            "correct_matches": correct_matches,
            "total_expected": total_expected,
        }