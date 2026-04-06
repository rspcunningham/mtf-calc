import webview


class Api:
    def greet(self, name):
        return f"Hello, {name}!"


if __name__ == "__main__":
    api = Api()
    window = webview.create_window("MTF Calculator", "ui/index.html", js_api=api)
    webview.start()
