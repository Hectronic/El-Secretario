from src.ui.welcome.pomodoro_labels import pomodoro_labels


def test_pomodoro_action_labels_are_localized_for_supported_documentation_languages():
    assert pomodoro_labels("en_US")["quick_focus"] == "Quick focus"
    assert pomodoro_labels("es_ES")["start"] == "Iniciar Pomodoro"
    assert pomodoro_labels("ast_ES")["open"] == "Abrir Pomodoro activu"
