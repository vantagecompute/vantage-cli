from vantage_cli.format import render_json, terminal_message


def test_terminal_message_basic(capsys):
    terminal_message("Hello World", subject="Greeting", color="blue", footer="Footer")
    out = capsys.readouterr().out
    assert "Greeting" in out
    assert "Hello World" in out
    assert "Footer" in out


def test_render_json_basic(capsys):
    render_json({"a": 1, "b": 2})
    out = capsys.readouterr().out
    assert '"a": 1' in out
    assert '"b": 2' in out
