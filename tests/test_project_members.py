"""Integration tests for project members command (Phase 1.5)."""

from __future__ import annotations


class TestProjectMembers:
    """Tests for project members listing."""

    def test_list_members_shared_project(self, client):
        """Home project (65502d0fdae691e5fd5ca316) returns members."""
        members = client.get_project_members("65502d0fdae691e5fd5ca316")
        # It's a shared project (userCount=2)
        assert isinstance(members, list)
        # Should have at least 1 member (the owner)
        assert len(members) >= 1

    def test_list_members_personal_project(self, client):
        """Personal project returns empty or owner-only."""
        members = client.get_project_members("69c85b6cd66d913b44d0570c")
        assert isinstance(members, list)

    def test_member_fields_present(self, client):
        """Member objects have expected fields."""
        members = client.get_project_members("65502d0fdae691e5fd5ca316")
        if members:
            member = members[0]
            # Each member should have at minimum userId
            assert "userId" in member or "id" in member
