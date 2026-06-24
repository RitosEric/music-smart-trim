# api/websocket.py
"""WebSocket handlers for real-time progress updates."""
from flask_socketio import emit, join_room, leave_room

def register_websocket_handlers(socketio):
    """Register WebSocket event handlers."""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        print('Client connected')
        emit('connected', {'message': 'Connected to server'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        print('Client disconnected')

    @socketio.on('join_job')
    def handle_join_job(data):
        """Join a job room to receive updates for specific job."""
        job_id = data.get('job_id')
        if job_id:
            join_room(job_id)
            emit('joined', {'job_id': job_id})
            print(f'Client joined job room: {job_id}')

    @socketio.on('leave_job')
    def handle_leave_job(data):
        """Leave a job room."""
        job_id = data.get('job_id')
        if job_id:
            leave_room(job_id)
            emit('left', {'job_id': job_id})
            print(f'Client left job room: {job_id}')


def emit_progress(socketio, job_id, message, progress):
    """
    Emit progress update to all clients in job room.

    Args:
        socketio: SocketIO instance
        job_id: Job identifier
        message: Progress message
        progress: Progress percentage (0-100)
    """
    socketio.emit('progress_update', {
        'job_id': job_id,
        'message': message,
        'progress': progress
    }, room=job_id)
