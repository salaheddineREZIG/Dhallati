from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use 5000
    port = int(os.getenv('PORT', 5000))
    
    # Determine if we're in production
    debug = os.getenv('FLASK_ENV') == 'development'
    
    # For production, use a production WSGI server instead
    # This should be run with: gunicorn run:app
    app.run(port=port, debug=debug, use_reloader=debug, host='0.0.0.0')