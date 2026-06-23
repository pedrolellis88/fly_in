"""Parse and validate individual Fly-in map declarations."""

from __future__ import annotations

from typing import Any

from src.Utils.connection_key import make_connection_key


class MapParserError(Exception):
    """Invalid syntax or data in a map file."""


class NumberParser:
    """Parse numeric values used by map declarations."""

    @staticmethod
    def parse_int(value: str, line_number: int, field: str) -> int:
        """Parse a signed integer."""
        if not value.lstrip("-").isdigit():
            raise MapParserError(
                f"Line {line_number}: {field} must be an integer, "
                f"got {value!r}."
            )

        return int(value)

    @staticmethod
    def parse_positive_int(value: str, line_number: int, field: str) -> int:
        """Parse a strictly positive integer."""
        if not value.isdigit():
            raise MapParserError(
                f"Line {line_number}: {field} must be a positive integer "
                f"greater than zero, got {value!r}."
            )

        parsed = int(value)
        if parsed <= 0:
            raise MapParserError(
                f"Line {line_number}: {field} must be a positive integer "
                f"greater than zero, got {value!r}."
            )

        return parsed


class MetadataParser:
    """Parse and validate metadata blocks."""

    VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}

    def split_tokens_and_metadata(
        self,
        text: str,
        line_number: int,
    ) -> tuple[list[str], str | None]:
        """Split positional tokens from an optional trailing metadata block."""
        if "]" in text and "[" not in text:
            raise MapParserError(
                f"Line {line_number}: unexpected closing bracket in {text!r}."
            )

        if "[" not in text:
            return text.split(), None

        open_index = text.index("[")
        close_index = text.find("]", open_index + 1)

        if close_index == -1:
            raise MapParserError(
                f"Line {line_number}: metadata block must end with ']'."
            )

        after = text[close_index + 1:].strip()
        if after:
            raise MapParserError(
                f"Line {line_number}: unexpected text after metadata block: "
                f"{after!r}."
            )

        tokens = text[:open_index].strip().split()
        metadata = text[open_index:close_index + 1].strip()
        return tokens, metadata

    def parse_zone_metadata(
        self,
        meta_raw: str | None,
        line_number: int,
    ) -> dict[str, Any]:
        """Parse optional metadata for a zone."""
        meta: dict[str, Any] = {
            "zone": "normal",
            "color": "none",
            "max_drones": 1,
        }

        if meta_raw is None:
            return meta

        pairs = self._parse_metadata_block(meta_raw, line_number)
        for key, value in pairs.items():
            if key == "zone":
                self._validate_zone_type(value, line_number)
                meta["zone"] = value
            elif key == "color":
                meta["color"] = value
            elif key == "max_drones":
                meta["max_drones"] = NumberParser.parse_positive_int(
                    value,
                    line_number,
                    "max_drones",
                )
            else:
                raise MapParserError(
                    f"Line {line_number}: unknown zone metadata key {key!r}."
                )

        return meta

    def parse_connection_metadata(
        self,
        meta_raw: str | None,
        line_number: int,
    ) -> dict[str, Any]:
        """Parse optional metadata for a connection."""
        meta: dict[str, Any] = {"max_link_capacity": 1}

        if meta_raw is None:
            return meta

        pairs = self._parse_metadata_block(meta_raw, line_number)
        for key, value in pairs.items():
            if key != "max_link_capacity":
                raise MapParserError(
                    f"Line {line_number}: unknown connection metadata key "
                    f"{key!r}."
                )

            meta["max_link_capacity"] = NumberParser.parse_positive_int(
                value,
                line_number,
                "max_link_capacity",
            )

        return meta

    def _parse_metadata_block(
        self,
        meta_raw: str,
        line_number: int,
    ) -> dict[str, str]:
        """Parse a raw metadata block of key=value pairs in brackets."""
        if not meta_raw.startswith("[") or not meta_raw.endswith("]"):
            raise MapParserError(
                f"Line {line_number}: metadata must be wrapped in brackets, "
                f"got {meta_raw!r}."
            )

        content = meta_raw[1:-1].strip()
        if not content:
            return {}

        pairs: dict[str, str] = {}
        for part in content.split():
            key, value = self._parse_metadata_entry(part, line_number)
            if key in pairs:
                raise MapParserError(
                    f"Line {line_number}: duplicate metadata key {key!r}."
                )
            pairs[key] = value

        return pairs

    def _parse_metadata_entry(
        self,
        part: str,
        line_number: int,
    ) -> tuple[str, str]:
        """Parse one key=value metadata entry."""
        if "=" not in part:
            raise MapParserError(
                f"Line {line_number}: metadata entry {part!r} is missing '='."
            )

        key, _, value = part.partition("=")

        if not key:
            raise MapParserError(
                f"Line {line_number}: metadata entry has an empty key."
            )
        if not value:
            raise MapParserError(
                f"Line {line_number}: metadata key {key!r} "
                "has an empty value."
            )

        return key, value

    def _validate_zone_type(self, value: str, line_number: int) -> None:
        """Validate a zone type metadata value."""
        if value not in self.VALID_ZONE_TYPES:
            raise MapParserError(
                f"Line {line_number}: invalid zone type {value!r}. "
                f"Valid types: {sorted(self.VALID_ZONE_TYPES)}."
            )


class ZoneParser:
    """Parse zone declarations."""

    def __init__(self, metadata_parser: MetadataParser) -> None:
        self._metadata_parser = metadata_parser

    def parse(
        self,
        line: str,
        line_number: int,
        prefix: str,
        data: dict[str, Any],
    ) -> None:
        """Parse and store a zone declaration."""
        rest = line.partition(":")[2].strip()
        tokens, meta_raw = self._metadata_parser.split_tokens_and_metadata(
            rest,
            line_number,
        )

        if len(tokens) != 3:
            raise MapParserError(
                f"Line {line_number}: invalid zone syntax. "
                f"Expected '<name> <x> <y>', got {tokens!r}."
            )

        zone_name, raw_x, raw_y = tokens
        self._validate_zone_name(zone_name, line_number, data)
        meta = self._metadata_parser.parse_zone_metadata(
            meta_raw,
            line_number,
        )

        data["zones"][zone_name] = {
            "name": zone_name,
            "x": NumberParser.parse_int(raw_x, line_number, "x coordinate"),
            "y": NumberParser.parse_int(raw_y, line_number, "y coordinate"),
            "zone_type": meta["zone"],
            "color": meta["color"],
            "max_drones": meta["max_drones"],
            "role": self._get_role(prefix),
        }

        self._store_special_hub(prefix, zone_name, line_number, data)

    def _validate_zone_name(
        self,
        zone_name: str,
        line_number: int,
        data: dict[str, Any],
    ) -> None:
        """Validate a zone name."""
        if not zone_name:
            raise MapParserError(
                f"Line {line_number}: zone name cannot be empty."
            )
        if "-" in zone_name:
            raise MapParserError(
                f"Line {line_number}: zone name {zone_name!r} "
                "cannot contain dashes."
            )
        if any(char.isspace() for char in zone_name):
            raise MapParserError(
                f"Line {line_number}: zone name {zone_name!r} "
                "cannot contain spaces."
            )
        if zone_name in data["zones"]:
            raise MapParserError(
                f"Line {line_number}: duplicate zone name {zone_name!r}."
            )

    def _get_role(self, prefix: str) -> str:
        """Return the internal role for a zone prefix."""
        if prefix == "start_hub":
            return "start"
        if prefix == "end_hub":
            return "end"
        return "normal"

    def _store_special_hub(
        self,
        prefix: str,
        zone_name: str,
        line_number: int,
        data: dict[str, Any],
    ) -> None:
        """Store start or end hub references when needed."""
        if prefix == "start_hub":
            if data["start"] is not None:
                raise MapParserError(
                    f"Line {line_number}: multiple start_hub definitions."
                )
            data["start"] = zone_name
        elif prefix == "end_hub":
            if data["end"] is not None:
                raise MapParserError(
                    f"Line {line_number}: multiple end_hub definitions."
                )
            data["end"] = zone_name


class ConnectionParser:
    """Parse connection declarations."""

    def __init__(self, metadata_parser: MetadataParser) -> None:
        self._metadata_parser = metadata_parser

    def parse(
        self,
        line: str,
        line_number: int,
        data: dict[str, Any],
        conn_keys: set[frozenset[str]],
    ) -> None:
        """Parse and store a connection declaration."""
        rest = line.partition(":")[2].strip()
        tokens, meta_raw = self._metadata_parser.split_tokens_and_metadata(
            rest,
            line_number,
        )

        if len(tokens) != 1 or "-" not in tokens[0]:
            raise MapParserError(
                f"Line {line_number}: invalid connection syntax. "
                f"Expected '<zone_a>-<zone_b>'."
            )

        zone_a, _, zone_b = tokens[0].partition("-")
        self._validate_connection_names(zone_a, zone_b, line_number)
        self._validate_zones_are_defined(
            zone_a,
            zone_b,
            line_number,
            data,
        )
        self._validate_not_duplicate(
            zone_a,
            zone_b,
            line_number,
            conn_keys,
        )
        meta = self._metadata_parser.parse_connection_metadata(
            meta_raw,
            line_number,
        )

        data["connections"].append({
            "from": zone_a,
            "to": zone_b,
            "max_link_capacity": meta["max_link_capacity"],
            "line": line_number,
        })
        conn_keys.add(make_connection_key(zone_a, zone_b))

    def _validate_connection_names(
        self,
        zone_a: str,
        zone_b: str,
        line_number: int,
    ) -> None:
        """Validate connection endpoint names."""
        if not zone_a or not zone_b:
            raise MapParserError(
                f"Line {line_number}: invalid connection. "
                "Zone name cannot be empty."
            )
        if zone_a == zone_b:
            raise MapParserError(
                f"Line {line_number}: self-connections are not allowed."
            )

    def _validate_zones_are_defined(
        self,
        zone_a: str,
        zone_b: str,
        line_number: int,
        data: dict[str, Any],
    ) -> None:
        """Validate that connection endpoints were declared earlier."""
        for zone_name in (zone_a, zone_b):
            if zone_name not in data["zones"]:
                raise MapParserError(
                    f"Line {line_number}: connection references undefined "
                    f"zone {zone_name!r}."
                )

    def _validate_not_duplicate(
        self,
        zone_a: str,
        zone_b: str,
        line_number: int,
        conn_keys: set[frozenset[str]],
    ) -> None:
        """Validate that a bidirectional connection was not declared before."""
        key = make_connection_key(zone_a, zone_b)

        if key in conn_keys:
            raise MapParserError(
                f"Line {line_number}: duplicate connection "
                f"{zone_a!r}-{zone_b!r}."
            )
