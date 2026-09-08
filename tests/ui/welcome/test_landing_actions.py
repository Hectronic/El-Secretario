from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication, QLineEdit, QListWidget, QPushButton

from src.ui.welcome.landing_actions import WelcomeLandingActions
from src.ui.welcome.landing_data import FavoritesPage, LandingListItem


_APP = QApplication.instance() or QApplication([])


class _Widget(QObject):
    search_triggered = pyqtSignal(str)
    result_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.search_input = QLineEdit()
        self.results_list = QListWidget()
        self.fav_list = QListWidget()
        self.today_list = QListWidget()
        self.prev_btn = QPushButton()
        self.next_btn = QPushButton()
        self.db = object()
        self.favorites_page = 0


def test_search_results_and_record_navigation_emit_expected_signals():
    widget = _Widget()
    actions = WelcomeLandingActions(widget)
    queries, record_ids = [], []
    widget.search_triggered.connect(queries.append)
    widget.result_clicked.connect(record_ids.append)

    widget.search_input.setText("  agenda  ")
    actions.trigger_search()
    actions.display_results(
        [{"id": 9, "distance": 0.2, "text": "Plan", "metadata": {"title": "Today"}}]
    )
    actions.open_item(widget.results_list.item(0))
    actions.display_results([])

    assert queries == ["agenda"]
    assert record_ids == [9]
    assert widget.results_list.isHidden()


def test_favorites_pagination_and_today_population(monkeypatch):
    widget = _Widget()
    actions = WelcomeLandingActions(widget)
    pages = {
        0: FavoritesPage(0, (LandingListItem(1, "First"),), False, True),
        1: FavoritesPage(1, (LandingListItem(2, "Second"),), True, False),
    }

    monkeypatch.setattr(
        "src.ui.welcome.landing_actions.fetch_favorites_page",
        lambda _db, *, page: pages[page],
    )
    monkeypatch.setattr(
        "src.ui.welcome.landing_actions.fetch_today_items",
        lambda _db: (LandingListItem(3, "Today"),),
    )

    actions.load_favorites()
    actions.next_page()
    actions.previous_page()
    actions.load_today()

    assert widget.favorites_page == 0
    assert widget.fav_list.item(0).data(Qt.ItemDataRole.UserRole) == 1
    assert widget.prev_btn.isEnabled() is False
    assert widget.next_btn.isEnabled() is True
    assert widget.today_list.item(0).data(Qt.ItemDataRole.UserRole) == 3
