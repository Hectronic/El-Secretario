"""Tabbed Qt composition for the tools facade."""

from PyQt6.QtWidgets import QLabel, QTabWidget, QVBoxLayout

from src.ui.batch_process_widget import BatchProcessWidget
from src.ui.summary_batch_widget import SummaryBatchWidget
from src.ui.task_batch_widget import TaskBatchWidget


def build_tools_view(widget):
    """Compose the tab shell and inject shared dependencies into batch views."""
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)

    title = QLabel("⚙️ Tools")
    title.setStyleSheet(
        "font-size: 28px; font-weight: bold; color: #607D8B; padding: 20px;"
    )
    layout.addWidget(title)

    widget.tabs = QTabWidget()

    widget.storage_widget = widget._create_storage_tab()
    widget.tabs.addTab(widget.storage_widget, "🗄️ Storage")

    widget.processing_widget = BatchProcessWidget(
        task_queue=widget.task_queue, persistence=widget.db
    )
    widget.tabs.addTab(widget.processing_widget, "⏳ Processing")

    widget.summary_widget = SummaryBatchWidget(
        task_queue=widget.task_queue, persistence=widget.db
    )
    widget.tabs.addTab(widget.summary_widget, "📝 Summaries")

    widget.tasks_batch_widget = TaskBatchWidget(
        task_queue=widget.task_queue, persistence=widget.db
    )
    widget.tabs.addTab(widget.tasks_batch_widget, "✅ Tasks")

    widget.data_widget = widget._create_data_tab()
    widget.tabs.addTab(widget.data_widget, "📦 Data")

    widget.rag_widget = widget._create_rag_tab()
    widget.tabs.addTab(widget.rag_widget, "🧠 RAG")

    layout.addWidget(widget.tabs)
