"""Tests for discovery models (AssignmentInfo, ClassMember, GroupInfo, CourseInfo)."""

import pytest
from pydantic import ValidationError

from brightspace_extractor.models import (
    AssignmentInfo,
    ClassMember,
    CourseInfo,
    GroupInfo,
)


class TestAssignmentInfo:
    def test_create(self) -> None:
        a = AssignmentInfo(assignment_id="336760", name="Power BI basis")
        assert a.assignment_id == "336760"
        assert a.name == "Power BI basis"

    def test_frozen(self) -> None:
        a = AssignmentInfo(assignment_id="1", name="Test")
        with pytest.raises(ValidationError):
            a.name = "Changed"


class TestClassMember:
    def test_create_student(self) -> None:
        m = ClassMember(name="Alice", org_defined_id="500123456", role="Student")
        assert m.name == "Alice"
        assert m.org_defined_id == "500123456"
        assert m.role == "Student"

    def test_create_lecturer(self) -> None:
        m = ClassMember(
            name="Jan-Ru Muller", org_defined_id="jrmulle", role="Designing Lecturer"
        )
        assert m.role == "Designing Lecturer"

    def test_frozen(self) -> None:
        m = ClassMember(name="A", org_defined_id="1", role="Student")
        with pytest.raises(ValidationError):
            m.role = "Lecturer"


class TestGroupInfo:
    def test_create(self) -> None:
        g = GroupInfo(group_name="FC2A - 1", category="FC2A", members="4/4")
        assert g.group_name == "FC2A - 1"
        assert g.category == "FC2A"
        assert g.members == "4/4"

    def test_empty_members(self) -> None:
        g = GroupInfo(group_name="FC2A - 8", category="FC2A", members="")
        assert g.members == ""

    def test_frozen(self) -> None:
        g = GroupInfo(group_name="G", category="C", members="1/1")
        with pytest.raises(ValidationError):
            g.members = "2/2"


class TestCourseInfo:
    def test_create(self) -> None:
        c = CourseInfo(class_id="698557", name="Data & Control [25/26, Blok 3]")
        assert c.class_id == "698557"
        assert c.name == "Data & Control [25/26, Blok 3]"

    def test_frozen(self) -> None:
        c = CourseInfo(class_id="1", name="Test")
        with pytest.raises(ValidationError):
            c.class_id = "2"
