from core.logger import setup_logger
from core.app import App


def main() -> None:
    setup_logger()
    app = App()
    app.run()
    # print(config.VARIABLE_1)


if __name__ == "__main__":
    main()
