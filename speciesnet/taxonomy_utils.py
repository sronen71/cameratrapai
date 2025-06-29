# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Taxonomy-related utility functions.

Provides functions for working with taxonomic labels, such as finding ancestors at
specific levels and extracting full class strings.
"""

from typing import Optional

from speciesnet.constants import Classification


def get_ancestor_at_level(
    label: str, taxonomy_level: str, taxonomy_map: dict
) -> Optional[str]:
    """Finds the taxonomy item corresponding to a label's ancestor at a given level.

    E.g. The ancestor at family level for
    `uuid;class;order;family;genus;species;common_name` is
    `another_uuid;class;order;family;;;another_common_name`.

    Args:
        label:
            String label for which to find the ancestor.
        taxonomy_level:
            One of "species", "genus", "family", "order", "class" or "kingdom",
            indicating the taxonomy level at which to find a label's ancestor.
        taxonomy_map:
            Dictionary mapping taxa to labels.

    Returns:
        A string label indicating the ancestor at the requested taxonomy level. In
        case the taxonomy doesn't contain the corresponding ancestor, return `None`.

    Raises:
        ValueError:
            If the given label is invalid.
    """

    label_parts = label.split(";")
    if len(label_parts) != 7:
        raise ValueError(
            f"Expected label made of 7 parts, but found only {len(label_parts)}: "
            f"{label}"
        )

    if taxonomy_level == "species":
        ancestor_parts = label_parts[1:6]
        if not ancestor_parts[4]:
            return None
    elif taxonomy_level == "genus":
        ancestor_parts = label_parts[1:5] + [""]
        if not ancestor_parts[3]:
            return None
    elif taxonomy_level == "family":
        ancestor_parts = label_parts[1:4] + ["", ""]
        if not ancestor_parts[2]:
            return None
    elif taxonomy_level == "order":
        ancestor_parts = label_parts[1:3] + ["", "", ""]
        if not ancestor_parts[1]:
            return None
    elif taxonomy_level == "class":
        ancestor_parts = label_parts[1:2] + ["", "", "", ""]
        if not ancestor_parts[0]:
            return None
    elif taxonomy_level == "kingdom":
        ancestor_parts = ["", "", "", "", ""]
        if not label_parts[1] and label != Classification.ANIMAL:
            return None
    else:
        return None

    ancestor = ";".join(ancestor_parts)
    return taxonomy_map.get(ancestor)


def get_full_class_string(label: str) -> str:
    """Extracts the full class string corresponding to a given label.

    E.g. The full class string for the label
    `uuid;class;order;family;genus;species;common_name` is
    `class;order;family;genus;species`.

    Args:
        label:
            String label for which to extract the full class string.

    Returns:
        Full class string for the given label.

    Raises:
        ValueError: If the given label is invalid.
    """

    label_parts = label.split(";")
    if len(label_parts) != 7:
        raise ValueError(
            f"Expected label made of 7 parts, but found only {len(label_parts)}: "
            f"{label}"
        )
    return ";".join(label_parts[1:6])


def get_species_to_sibling_species_map(taxonomy_map: dict) -> dict[str, list[str]]:
    """
    Returns a mapping from each species label to a list of all other species labels in the same genus.

    Args:
        taxonomy_map: Dictionary mapping taxa (full class strings) to labels.

    Returns:
        Dictionary where keys are species labels (full label strings) and values are lists of sibling species labels (excluding itself).
    """
    species_taxa = [taxa for taxa in taxonomy_map.values()]
    genus_to_species = {}
    for taxa in species_taxa:
        genus = taxa.split(";")[:5]
        if genus:
            genus_to_species.setdefault(genus, []).append(taxa)
    species_to_siblings = {}
    for taxa in species_taxa:
        genus = taxa.split(";")[:5]
        if genus:
            siblings = [sib_taxa for sib_taxa in genus_to_species[genus] if sib_taxa != taxa]
            species_to_siblings[taxa] = siblings
    return species_to_siblings


def get_genus_to_species_dict(taxonomy_map: dict) -> dict[tuple, list[str]]:
    """
    Returns a mapping from genus (as a tuple of class, order, family, genus) to a list of all species labels in that genus.

    Args:
        taxonomy_map: Dictionary mapping taxa (full class strings) to labels.

    Returns:
        Dictionary where keys are genus tuples and values are lists of species labels (full label strings).
    """
    species_labels = [label for label in taxonomy_map.values() if isinstance(label, str) and label.count(";") == 6]
    genus_to_species = {}
    for label in species_labels:
        genus_tuple = tuple(label.split(";")[:5])
        if all(genus_tuple):
            genus_to_species.setdefault(genus_tuple, []).append(label)
    return genus_to_species


def get_sibling_species(label: str, genus_to_species: dict) -> list[str]:
    """
    Returns a list of sibling species labels for the given label using the genus_to_species dict.

    Args:
        label: Full label string for the species.
        genus_to_species: Dict mapping genus tuples to lists of species labels.

    Returns:
        List of sibling species labels (excluding the input label).
    """
    genus_tuple = tuple(label.split(";")[:5])
    siblings = [l for l in genus_to_species.get(genus_tuple, []) if l != label]
    return siblings
