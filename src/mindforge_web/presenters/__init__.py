"""Web presenter helpers.

中文学习型说明：presenters/ 模块包含 Web API 的纯数据变换函数。
每个 presenter 负责一类 domain 对象 → Pydantic response 的映射，
不包含 IO、副作用或业务规则。
"""

from mindforge_web.presenters.shared import get_relation_reason_label, make_relation_record
from mindforge_web.presenters.graph_presenter import (
    build_graph_builder,
    build_graph_edge_response,
    build_graph_node_response,
    build_graph_response,
    build_local_graph_response,
    get_graph_neighbor_count,
    resolve_card_id,
)
from mindforge_web.presenters.library_presenter import (
    build_library_card_response,
    build_library_card_summary_response,
    build_library_detail_response,
    build_library_relationship_context,
    build_library_stats_response,
    build_related_card_responses,
)
from mindforge_web.presenters.discovery_presenter import (
    build_discovery_context_response,
    compute_related_sources,
    get_center_card_communities,
)
from mindforge_web.presenters.provenance_presenter import build_provenance_trail_response
from mindforge_web.presenters.web_errors import http_error, user_error
from mindforge_web.presenters.web_status import bool_status

__all__ = [
    # shared
    "get_relation_reason_label",
    "make_relation_record",
    # graph
    "build_graph_builder",
    "build_graph_edge_response",
    "build_graph_node_response",
    "build_graph_response",
    "build_local_graph_response",
    "get_graph_neighbor_count",
    "resolve_card_id",
    # library
    "build_library_card_response",
    "build_library_card_summary_response",
    "build_library_detail_response",
    "build_library_relationship_context",
    "build_library_stats_response",
    "build_related_card_responses",
    # discovery
    "build_discovery_context_response",
    "compute_related_sources",
    "get_center_card_communities",
    # provenance
    "build_provenance_trail_response",
    # errors
    "http_error",
    "user_error",
    # status
    "bool_status",
]
