from flask import request
@app.route('/api/debug_headers')
def debug_headers():
    return str(request.headers)
