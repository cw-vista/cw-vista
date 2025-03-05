"""
JSON schema to validate CW search data
"""

__author__ = "Karl Wette <karl.wette@anu.edu.au>"
__copyright__ = "Copyright (C) 2025 Karl Wette"


def get():

    range_anyof_items = []
    for range_item_req in (
        ["freq"],
        ["freq", "bin-a-sin-i", "bin-period"],
        ["freq", "bin-freq-mod-depth", "bin-period"],
    ):
        range_anyof_items.append(
            {
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": range_item_req,
                    "properties": {
                        "freq": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": True,
                            "items": {
                                "type": "number",
                                "exclusiveMinimum": 0,
                            },
                        },
                        "fdot": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": True,
                            "items": {
                                "type": "number",
                            },
                        },
                        "fddot": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": True,
                            "items": {
                                "type": "number",
                            },
                        },
                        "bin-a-sin-i": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": True,
                            "items": {
                                "type": "number",
                            },
                        },
                        "bin-freq-mod-depth": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": True,
                            "items": {
                                "type": "number",
                                "exclusiveMinimum": 0,
                            },
                        },
                        "bin-period": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": True,
                            "items": {
                                "type": "number",
                                "exclusiveMinimum": 0,
                            },
                        },
                        "bin-time-asc": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "uniqueItems": True,
                            "items": {
                                "type": "number",
                                "exclusiveMinimum": 0,
                            },
                        },
                    },
                }
            }
        )

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["reference", "searches"],
        "properties": {
            "reference": {
                "oneOf": [
                    {"type": "string", "const": "unpublished"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "author",
                            "title",
                            "journal",
                            "volume",
                            "pages",
                            "year",
                            "doi",
                            "key-suffix",
                        ],
                        "properties": {
                            "author": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "string",
                                    "pattern": r"^([^,]+,[^,]+|others)$",
                                },
                            },
                            "collaboration": {
                                "type": "array",
                                "minItems": 1,
                                "items": {"type": "string", "pattern": r"^[^,]+$"},
                            },
                            "title": {"type": "string"},
                            "journal": {"type": "string"},
                            "volume": {"type": "string", "pattern": r"^[A-Z0-9]+$"},
                            "pages": {"type": "string", "pattern": r"^[A-Z0-9]+$"},
                            "year": {"type": "integer", "minimum": 2000},
                            "doi": {
                                "type": "string",
                                "pattern": r'^10[.][0-9]{4,}[^\s"\/<>]*\/[^\s"<>]+$',
                            },
                            "key": {"type": "string"},
                            "key-suffix": {"type": "string", "pattern": r"^[a-z]$"},
                        },
                    },
                ],
            },
            "searches": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "category",
                        "obs-run",
                        "algorithm-coherent",
                        "algorithm-incoherent",
                        "time-span",
                        "max-coherence-time",
                        "depth",
                        "param-space",
                    ],
                    "properties": {
                        "category": {
                            "type": "string",
                            "pattern": r"^(pulsar targeted|pulsar narrowband|cco|lmxb|skypatch|allsky isolated|allsky binary)$",
                        },
                        "astro-target": {"type": "string"},
                        "obs-run": {
                            "type": "string",
                            "pattern": r"^(S1|S2|S4|S5|S6|VSR1|VSR2|VSR4|O[1-9])$",
                        },
                        "algorithm-coherent": {"type": "string"},
                        "algorithm-incoherent": {"type": "string"},
                        "time-span": {"type": "number", "exclusiveMinimum": 0},
                        "max-coherence-time": {"type": "number", "exclusiveMinimum": 0},
                        "depth": {"type": "number", "exclusiveMinimum": 0},
                        "breadth": {"type": "number", "exclusiveMinimum": 0},
                        "param-space": {
                            "type": "object",
                            "additionalProperties": False,
                            "oneOf": [
                                {
                                    "required": ["num-pulsars"],
                                },
                                {
                                    "required": ["ranges"],
                                },
                            ],
                            "properties": {
                                "num-pulsars": {"type": "integer", "minimum": 1},
                                "sky-fraction": {
                                    "type": "number",
                                    "exclusiveMinimum": 0,
                                    "maximum": 1,
                                },
                                "hmm-num-jumps": {
                                    "type": "integer",
                                    "minimum": 1,
                                },
                                "ranges": {
                                    "type": "array",
                                    "minItems": 1,
                                    "anyOf": range_anyof_items,
                                },
                            },
                        },
                    },
                },
            },
        },
    }
