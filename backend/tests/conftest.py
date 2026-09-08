import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clean_db(app):
    """各テストの前後でテーブルをクリアし、テスト間の状態漏れを防ぐ。"""
    with app.app_context():
        _db.session.remove()
        _db.drop_all()
        _db.create_all()
    yield
