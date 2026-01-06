import logging

from core import logger
from core.app import App


# Die Hauptfunktion des Projekts
def main() -> None:
	# Logger einrichten für einfaches Debugging
	logger.setup()

	# App starten
	try:
		app = App()
		app.run()
	except Exception as exception:
		logging.error(exception)


# Hauptfunktion ausführen
if __name__ == "__main__":
	main()
