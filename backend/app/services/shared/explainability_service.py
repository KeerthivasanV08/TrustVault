class ExplainabilityService:

    def generate_report(self, control_res: dict, ml_res: dict, graph_res: dict) -> list:
        evidence = []

        # 1. REGULATORY (CONTROL) EVIDENCE
        # Handles strings or lists from the Regulatory Engine
        reasons = control_res.get("reason", [])
        if isinstance(reasons, str):
            reasons = [reasons]
            
        for r in reasons:
            if r not in ["COMPLIANT", "WHITELISTED_USER"]:
                evidence.append({
                    "category": "REGULATORY",
                    "finding": f"Policy Violation: {r}"
                })

        # 2. BEHAVIORAL (ML) EVIDENCE
        for r in ml_res.get("reasons", []):
            explanation = self.translate_behavior(r)
            evidence.append({
                "category": "BEHAVIOR",
                "finding": explanation
            })

        # 3. NETWORK (GRAPH) EVIDENCE
        # Logic for hop distance and specific roles
        for r in graph_res.get("reasons", []):
            if r != "NO_MAJOR_GRAPH_RISK":
                explanation = self.translate_graph(r)
                evidence.append({
                    "category": "NETWORK",
                    "finding": explanation
                })

        # Specialized Graph Logic
        if graph_res.get("fraud_hop_distance", 999) <= 2:
            evidence.append({
                "category": "NETWORK",
                "finding": f"High Proximity to Fraud: {graph_res.get('exposure_type', 'Indirect')}"
            })

        if graph_res.get("network_role") in ["SINK_NODE", "COLLECTOR_HUB", "BRIDGE_LAYER", "SOURCE_DISTRIBUTOR"]:
            evidence.append({
                "category": "NETWORK",
                "finding": f"Suspect Role: {graph_res.get('network_role')}"
            })

        # Fallback if clean
        if not evidence:
            evidence.append({
                "category": "SUMMARY",
                "finding": "No high-risk anomalies detected across engines."
            })

        return evidence

    # =========================================================
    # TRANSLATORS (Human-Readable Mapping)
    # =========================================================

    def translate_behavior(self, reason: str) -> str:
        mapping = {
            "SLOW_BLEED_PATTERN": "24h cumulative velocity indicates slow-drain behavior.",
            "GATHER_SCATTER_MULE_PATTERN": "Account exhibits gather-scatter mule characteristics.",
            "RAPID_IN_OUT_RELAY": "Funds rapidly forwarded after inbound credit.",
            "STRUCTURED_FRAGMENTATION": "Near-threshold structuring (smurfing) detected.",
            "NEW_USER_HIGH_VALUE": "New account attempting unusually high-value first transaction."
        }
        return mapping.get(reason, reason)

    def translate_graph(self, reason: str) -> str:
        mapping = {
            "TEMPORAL_LAYERING_CHAIN": "Rapid multi-hop laundering chain detected.",
            "DIRECT_FRAUD_EXPOSURE": "Direct exposure to known fraudulent node.",
            "MULE_RING_CLUSTER": "User connected to synthetic mule cluster.",
            "NETWORK_ROLE_COLLECTOR_HUB": "Account behaves like a collector hub in the graph.",
            "NETWORK_ROLE_SINK_NODE": "Account behaves like a sink node in the graph.",
            "NETWORK_ROLE_BRIDGE_LAYER": "Account bridges multiple graph communities.",
            "NETWORK_ROLE_SOURCE_DISTRIBUTOR": "Account distributes funds across the graph.",
            "SHARED_DEVICE_CLUSTER": "Account shares device infrastructure with nearby peers.",
            "SHARED_IP_CLUSTER": "Account shares IP infrastructure with nearby peers.",
            "COORDINATED_TRANSFER_PATTERN": "Nearby graph activity looks coordinated.",
            "NEAR_FRAUD_CLUSTER": "Account is close to a known fraudulent node.",
            "GRAPH_ENGINE_UNAVAILABLE": "Graph analysis skipped due to engine timeout."
        }
        return mapping.get(reason, reason)