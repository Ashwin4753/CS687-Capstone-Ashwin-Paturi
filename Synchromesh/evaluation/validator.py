class GroundTruthValidator:
    def verify_accuracy(self, agent_output: List[Dict], expected_output: List[Dict]):
        """
        Checks if the agent correctly identified the right token for the right hex code.
        """
        correct_matches = 0
        total_expected = len(expected_output)
        
        for agent_rec in agent_output:
            for gold_rec in expected_output:
                if agent_rec['original_value'] == gold_rec['original_value'] and \
                   agent_rec['proposed_token'] == gold_rec['proposed_token']:
                    correct_matches += 1
        
        accuracy = (correct_matches / total_expected) * 100 if total_expected > 0 else 0
        return {"accuracy": accuracy, "matches": correct_matches}