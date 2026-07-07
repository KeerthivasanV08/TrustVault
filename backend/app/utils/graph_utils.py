def calculate_degree_centrality(edges, user_id):
    return len(edges)


def detect_funnel_pattern(inbound, outbound):
    return len(inbound) > 5 and len(outbound) <= 1