"""
config.py はモジュール読み込み時に os.environ.get(...) でクラス属性を
一度だけ決めているため、プロセス起動後に os.environ を書き換えても
(pytestのmonkeypatchのように)反映されない。実運用でも env は必ず
プロセス起動前に確定しているため、ここでは実際に別プロセスを起動して
確認する(プロセス起動前にenvを設定する、という現実の使われ方に合わせる)。
"""
import os
import subprocess
import sys

_CHECK_SNIPPET = "from app import create_app; create_app({config!r})"
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_in_subprocess(config_name: str, env_overrides: dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("SECRET_KEY", None)
    env.pop("JWT_SECRET_KEY", None)
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", _CHECK_SNIPPET.format(config=config_name)],
        cwd=_BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_production_rejects_default_secret_keys():
    """SECRET_KEY / JWT_SECRET_KEYを.envで設定し忘れたまま
    FLASK_ENV=productionで起動しようとすると、デフォルトの
    プレースホルダー秘密鍵のままでは起動できないこと。"""
    result = _run_in_subprocess("production", {})
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


def test_production_boots_with_real_secret_keys():
    """十分な秘密鍵が(.envまたはOS環境変数で)設定されていれば、
    本番設定でも問題なく起動できること。"""
    result = _run_in_subprocess(
        "production",
        {
            "SECRET_KEY": "a-sufficiently-long-random-secret-key-value",
            "JWT_SECRET_KEY": "another-sufficiently-long-random-secret",
            "DATABASE_URL": "sqlite:///:memory:",
        },
    )
    assert result.returncode == 0, result.stderr


def test_development_allows_default_secret_keys():
    """開発環境(FLASK_ENV=development、デフォルト)では、従来通り
    デフォルトの秘密鍵のままでも起動できること
    (このガードは本番設定のときだけ働く)。"""
    result = _run_in_subprocess("development", {})
    assert result.returncode == 0, result.stderr


def test_dotenv_file_is_actually_loaded(tmp_path):
    """README/HANDOFFの手順(.env.exampleを.envにコピーして値を埋める)
    通りに.envファイルを置いた場合、そこに書いた値がちゃんと読み込まれる
    こと(以前はload_dotenv()がどこからも呼ばれておらず、.envの内容が
    すべて無視されていた)。"""
    env_file = os.path.join(_BACKEND_ROOT, ".env")
    backup = None
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            backup = f.read()
    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(
                "SECRET_KEY=value-loaded-from-dot-env-file-abc123\n"
                "JWT_SECRET_KEY=another-value-from-dot-env-file-xyz\n"
                "DATABASE_URL=sqlite:///:memory:\n"
            )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from app.config import BaseConfig; "
                "assert BaseConfig.SECRET_KEY == 'value-loaded-from-dot-env-file-abc123', "
                "BaseConfig.SECRET_KEY",
            ],
            cwd=_BACKEND_ROOT,
            env={k: v for k, v in os.environ.copy().items() if k not in ("SECRET_KEY", "JWT_SECRET_KEY")},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
    finally:
        if backup is not None:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(backup)
        elif os.path.exists(env_file):
            os.remove(env_file)
