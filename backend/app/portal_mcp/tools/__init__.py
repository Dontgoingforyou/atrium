"""Регистрация тулов HTTP MCP."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.portal_mcp.tools import comms, documents, files, session, specialists, tasks


def register_tools(mcp: FastMCP) -> None:
    session.register(mcp)
    tasks.register(mcp)
    documents.register(mcp)
    specialists.register(mcp)
    comms.register(mcp)
    files.register(mcp)
