# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import warnings


_SENTENCEPIECE_SWIG_DEPRECATION_MESSAGES = (
    r"builtin type SwigPyPacked has no __module__ attribute",
    r"builtin type SwigPyObject has no __module__ attribute",
    r"builtin type swigvarlink has no __module__ attribute",
)


def suppress_sentencepiece_swig_deprecation_warnings() -> None:
    """Hide known Python 3.12 SWIG warnings emitted by sentencepiece."""
    for message in _SENTENCEPIECE_SWIG_DEPRECATION_MESSAGES:
        warnings.filterwarnings(
            "ignore",
            message=message,
            category=DeprecationWarning,
        )


def get_or_create_collection_compatible(client, name: str, embedding_fn):
    """
    Open/create a collection while tolerating embedding-function conflicts
    with previously persisted Chroma configurations.
    """
    try:
        return client.get_or_create_collection(
            name=name,
            embedding_function=embedding_fn,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "embedding function" in msg and ("conflict" in msg or "already exists" in msg):
            logging.warning(
                "Embedding function conflict for collection '%s'. Reusing existing collection configuration.",
                name,
            )
            return client.get_or_create_collection(name=name)
        raise
