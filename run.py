from app import create_app
from app.utils.helpers import _env_bool, _env_str

app = create_app()

if __name__ == '__main__':
    host = _env_str('APP_HOST', '127.0.0.1')
    port = int(_env_str('APP_PORT', '5000') or '5000')
    debug = _env_bool('FLASK_DEBUG', default=False)
    app.run(debug=debug, host=host, port=port)
