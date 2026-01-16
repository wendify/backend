from core import logger
from core.app import App


def main() -> None:
	logger.setup()

	app = App()
	app.run()


if __name__ == "__main__":
	main()
