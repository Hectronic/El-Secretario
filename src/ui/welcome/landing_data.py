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

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LandingListItem:
    record_id: int
    text: str


@dataclass(frozen=True)
class FavoritesPage:
    page: int
    items: tuple[LandingListItem, ...]
    has_previous: bool
    has_next: bool


def search_result_items(results) -> tuple[LandingListItem, ...]:
    items = []
    for result in results:
        title = result["metadata"].get("title", "Untitled")
        score = 1 - result["distance"]
        text = f"{title} (Score: {score:.2f})\n{result['text'][:100]}..."
        items.append(LandingListItem(record_id=result["id"], text=text))
    return tuple(items)


def fetch_favorites_page(db, *, page: int, page_size: int = 5) -> FavoritesPage:
    current_page = max(0, page)
    favorites = db.fetch_favorites(limit=page_size, offset=current_page * page_size)

    while not favorites and current_page > 0:
        current_page -= 1
        favorites = db.fetch_favorites(limit=page_size, offset=current_page * page_size)

    items = []
    for favorite in favorites:
        title = favorite["title"] if favorite["title"] else favorite["created_at"]
        items.append(
            LandingListItem(
                record_id=favorite["id"],
                text=f"{title} ({favorite['duration']:.1f}s)",
            )
        )

    next_batch = db.fetch_favorites(limit=1, offset=(current_page + 1) * page_size)
    return FavoritesPage(
        page=current_page,
        items=tuple(items),
        has_previous=current_page > 0,
        has_next=bool(next_batch),
    )


def fetch_today_items(db, *, today: date | None = None) -> tuple[LandingListItem, ...]:
    current_date = today or date.today()
    today_str = current_date.isoformat()
    records = db.fetch_by_date_range(today_str, today_str)

    items = []
    for record in records:
        if record.get("type") == "note":
            title = record["title"] if record["title"] else "Untitled Note"
            text = f"📝 {title}"
        else:
            title = record["title"] if record["title"] else record["created_at"]
            duration = record.get("duration", 0)
            text = f"🎤 {title} ({duration:.1f}s)"
        items.append(LandingListItem(record_id=record["id"], text=text))
    return tuple(items)
