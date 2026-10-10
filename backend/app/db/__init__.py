"""Supabase data access layer.

All reads/writes to Supabase go through this package. Route handlers should
call functions from the domain modules here instead of querying Supabase
directly. See supabase/README.md for connection setup.
"""
