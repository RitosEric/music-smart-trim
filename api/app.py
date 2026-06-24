# api/app.py
"""Flask application for Music Smart Trim API."""
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

    # Enable CORS for frontend
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize SocketIO for real-time updates
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

    # Register blueprints
    from api.routes import api
    app.register_blueprint(api)

    # Register WebSocket handlers
    from api.websocket import register_websocket_handlers
    register_websocket_handlers(socketio)

    # Store socketio instance in app config for access in routes
    app.config['SOCKETIO'] = socketio

    return app, socketio


if __name__ == '__main__':
    import os
    app, socketio = create_app()
    port = int(os.environ.get('PORT', 5002))
    socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
