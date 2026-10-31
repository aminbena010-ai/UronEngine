from types import SimpleNamespace

from IDE.ui.IM import MainWindow


def _restart_window(save_result):
    calls = []
    window = SimpleNamespace(
        restart_requested=False,
        save_scene=lambda: calls.append("save") or save_result,
        play_mode=SimpleNamespace(stop=lambda: calls.append("stop_play")),
        pytest_runner=SimpleNamespace(stop=lambda: calls.append("stop_tests")),
        close=lambda: calls.append("close"),
    )
    MainWindow.restart_editor(window)
    return window, calls


def test_restart_editor_saves_and_stops_processes_before_closing():
    window, calls = _restart_window(True)

    assert calls == ["save", "stop_play", "stop_tests", "close"]
    assert window.restart_requested


def test_restart_editor_does_not_close_when_saving_fails():
    window, calls = _restart_window(False)

    assert calls == ["save"]
    assert not window.restart_requested
