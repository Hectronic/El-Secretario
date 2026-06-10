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

from typing import Any, Dict, List, Optional


def build_search_where_clause(
    where_clause: Optional[Dict[str, Any]],
    ids: Optional[List[str]],
) -> Dict[str, Any]:
    final_where = {}
    if where_clause:
        final_where = where_clause.copy()

    if ids:
        if len(ids) == 1:
            final_where["id"] = ids[0]
        else:
            final_where["id"] = {"$in": ids}

    deleted_filter = {"deleted": {"$ne": "1"}}
    if final_where:
        return {"$and": [final_where, deleted_filter]}
    return deleted_filter

