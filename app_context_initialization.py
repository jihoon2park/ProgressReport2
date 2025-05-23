# shell_init.py
from your_app import create_app

app = create_app()
ctx = app.app_context()
ctx.push()  # This makes the context active

# Add any additional initialization code here