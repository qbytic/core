from app_init import app
from routes import admin, clan, user

if __name__ == "__main__":
    app.run(debug=True)
