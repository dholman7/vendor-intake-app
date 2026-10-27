"""Tenant-scoped data access.

Every read takes `tenant_id`. A record owned by another tenant is indistinguishable from a
missing one, and no method returns rows across tenants.
"""
