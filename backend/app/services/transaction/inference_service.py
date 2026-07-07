from app.services.transaction.ml_behavior_service import MLBehaviorService
from app.services.transaction.sequence_model_service import SequenceModelService
from app.services.transaction.graph_service import GraphIntelligenceEngine


class InferenceService:

    def __init__(self):

        self.behavior = MLBehaviorService()

        self.sequence = SequenceModelService()

        self.graph = GraphIntelligenceEngine()

    def run_inference(

        self,
        txn,
        velocity_context,
        onboarding_context,
        graph_context,
        recent_transactions

    ):

        behavioral = self.behavior.predict(

            txn,
            velocity_context,
            onboarding_context

        )

        sequence = self.sequence.detect_sequence_anomaly(
            recent_transactions
        )

        graph_embedding = self.graph.evaluate_graph_risk(
            str((graph_context or {}).get("user_id") or (txn or {}).get("sender_id") or ""),
            txn or {},
        )

        return {

            "behavioral":
                behavioral,

            "sequence":
                sequence,

            "graph_embedding":
                graph_embedding,

            "graph_result":
                graph_embedding

        }