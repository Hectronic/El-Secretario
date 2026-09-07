from PyQt6.QtCore import QPoint, QSize, Qt

from src.ui.main_window.floating_chat_host import FloatingChatHost


def test_host_clamps_preferred_size_to_configured_bounds(qtbot):
    host = FloatingChatHost()
    qtbot.addWidget(host)
    host.set_size_bounds(QSize(300, 200), QSize(500, 400))

    host.set_preferred_size(QSize(900, 100))

    assert host.size() == QSize(500, 200)
    assert host.sizeHint() == QSize(500, 200)


def test_host_disables_resize_edges_when_minimized(qtbot):
    host = FloatingChatHost()
    qtbot.addWidget(host)
    host.set_preferred_size(QSize(420, 380))
    host.set_resize_enabled(False)

    assert host._resize_edges_for_pos(QPoint(0, 0)) == host.EDGE_NONE
    assert host._cursor_for_edges(host.EDGE_LEFT) == Qt.CursorShape.SizeHorCursor
