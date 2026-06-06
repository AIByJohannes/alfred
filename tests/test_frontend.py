def test_app_ui_imports():
    from frontend.app import app_ui, server, App

    assert app_ui is not None
    assert callable(server)


def test_app_constructs():
    from frontend.app import app, server

    assert callable(app)
    assert callable(server)
