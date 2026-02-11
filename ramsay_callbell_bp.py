"""
Public route for Ramsay Callbell Monitor (no login required).
Serves the callbell UI at /ramsay-callbell which connects via SocketIO
to the standalone ramsay server running on port 5000.
"""
from flask import Blueprint, render_template

ramsay_callbell_bp = Blueprint('ramsay_callbell', __name__)


@ramsay_callbell_bp.route('/ramsay-callbell')
def ramsay_callbell():
    """Public callbell monitor page — no login required."""
    return render_template('ramsay_callbell.html')
