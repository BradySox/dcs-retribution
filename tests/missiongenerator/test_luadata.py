"""LuaData serialization: an item may carry scalars and nested objects at once."""

from __future__ import annotations

from game.missiongenerator.luagenerator import LuaData


def test_a_record_keeps_its_scalars_beside_a_nested_list() -> None:
    """Serializing only the nested half silently drops every add_key_value.

    A record that carries a name beside a list of points reached the Lua with
    the list and no name, and a plugin reading that name saw an empty string and
    took its "nothing to do" exit -- no error, no log line, the feature simply
    never happened.
    """
    data = LuaData("root")
    record = data.add_item("thing")
    record.add_key_value("name", "Kola")
    children = record.get_or_create_item("points")
    child = children.add_item()
    child.add_key_value("x", "1")

    out = data.serialize()

    assert 'name = "Kola"' in out, "the scalar was dropped beside the nested list"
    assert 'x = "1"' in out, "the nested list was dropped"


def test_scalars_only_still_serialize() -> None:
    data = LuaData("root")
    record = data.add_item("thing")
    record.add_key_value("a", "1")
    record.add_key_value("b", "2")
    out = data.serialize()
    assert 'a = "1"' in out and 'b = "2"' in out


def test_objects_only_still_serialize() -> None:
    data = LuaData("root")
    record = data.add_item("thing")
    record.get_or_create_item("kids").add_item().add_key_value("x", "1")
    assert 'x = "1"' in data.serialize()
