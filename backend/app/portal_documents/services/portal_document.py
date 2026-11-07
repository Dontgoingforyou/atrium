from __future__ import annotations

from app.core.text_search import escape_ilike_pattern as _escape_ilike_pattern
from app.portal_documents.services.portal_document_diff import compute_document_field_diff
from app.portal_documents.services.portal_document_duplicate import duplicate_document_subtree
from app.portal_documents.services.portal_document_mutations import (
    create_document,
    update_document,
    write_document_history,
)
from app.portal_documents.services.portal_document_queries import (
    assert_no_document_parent_cycle,
    batch_get_documents_light,
    count_documents,
    developer_docs_readable_ids,
    document_subtree_ids,
    ensure_user_can_read_document,
    get_ancestor_titles_for_breadcrumb,
    get_document,
    is_document_in_developer_docs_subtree,
    list_child_documents,
    list_document_history,
    list_documents,
    readable_document_ids_for_user,
    search_documents,
    virtual_nav_slug_for_document,
)
from app.portal_documents.services.portal_document_reorder import reorder_document_among_siblings
from app.portal_documents.services.portal_document_trash import (
    DOCUMENT_TRASH_TTL_DAYS,
    count_trash_document_roots,
    list_trash_document_roots,
    permanently_purge_document,
    restore_document,
    soft_delete_document,
)
from app.services.portal_tags import list_tags, replace_document_tags

__all__ = [
    # tags
    "list_tags",
    "replace_document_tags",
    # queries
    "_escape_ilike_pattern",
    "batch_get_documents_light",
    "get_document",
    "get_ancestor_titles_for_breadcrumb",
    "ensure_user_can_read_document",
    "list_documents",
    "count_documents",
    "list_child_documents",
    "assert_no_document_parent_cycle",
    "document_subtree_ids",
    "developer_docs_readable_ids",
    "readable_document_ids_for_user",
    "is_document_in_developer_docs_subtree",
    "virtual_nav_slug_for_document",
    "search_documents",
    "list_document_history",
    # mutations
    "compute_document_field_diff",
    "write_document_history",
    "create_document",
    "update_document",
    "duplicate_document_subtree",
    # trash / reorder
    "DOCUMENT_TRASH_TTL_DAYS",
    "soft_delete_document",
    "restore_document",
    "permanently_purge_document",
    "list_trash_document_roots",
    "count_trash_document_roots",
    "reorder_document_among_siblings",
]
