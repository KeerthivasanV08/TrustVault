from pydantic import BaseModel
from typing import List


class GraphEdge(BaseModel):
    from_node: str
    to_node: str
    amount: float
    timestamp: str


class GraphNode(BaseModel):
    user_id: str
    risk_score: float
    cluster_id: int
    is_mule: bool


class GraphQueryRequest(BaseModel):
    user_id: str
    hops: int = 2