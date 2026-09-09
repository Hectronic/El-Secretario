"""Compatibility facade for reusable Qt component widgets.

New code should import from :mod:`src.ui.component_widgets` families.
"""

from src.ui.component_widgets.rows import (
    RecordingListItemWidget,
    SummaryListItemWidget,
    TaskRowWidget,
)
from src.ui.component_widgets.sidebar import (
    SidebarChatSessionWidget,
    SidebarTaskCompactWidget,
)
from src.ui.component_widgets.tags import TagsLineEdit, create_tag_chip

__all__ = [
    "RecordingListItemWidget", "SidebarChatSessionWidget", "SidebarTaskCompactWidget",
    "SummaryListItemWidget", "TagsLineEdit", "TaskRowWidget", "create_tag_chip",
]
