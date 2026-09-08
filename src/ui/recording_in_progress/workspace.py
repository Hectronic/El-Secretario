"""Quick-task workspace helpers for an active recording."""


def add_quick_task(task_input, quick_tasks_list):
    text = task_input.text().strip()
    if not text:
        return False
    quick_tasks_list.addItem(text)
    task_input.clear()
    return True


def remove_selected_quick_tasks(quick_tasks_list):
    for item in quick_tasks_list.selectedItems():
        quick_tasks_list.takeItem(quick_tasks_list.row(item))


def quick_task_contents(quick_tasks_list):
    return [
        item.text().strip()
        for index in range(quick_tasks_list.count())
        if (item := quick_tasks_list.item(index)) and item.text().strip()
    ]
