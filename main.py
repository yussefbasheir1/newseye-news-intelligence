"""
main.py — NewsEye News Intelligence Dashboard
Entry point
"""
from dashboard import NewsEyeDashboard

if __name__ == "__main__":
    app = NewsEyeDashboard()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
