from crisisroute.api import create_app

app = create_app(database_url="sqlite:///crisisroute.db")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
