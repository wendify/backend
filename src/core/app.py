import datetime
import logging

from core.erzeuger import ErzeugerArt
from core.setup.smard import Smard


class App:
	def __init__(self) -> None:
		self.smard = Smard()

	def run(self) -> None:
		logging.info("Anwendung gestartet")

		datum = datetime.datetime(2025, 1, 2, 12, 30)
		erzeuger = self.smard.get_erzeuger(ErzeugerArt.Photovoltaik)

		print("\nInstallierter Wert:")
		print(erzeuger.installiert.get_row(datum))

		print("\nRealisierter Wert:")
		print(erzeuger.realisiert.get_row(datum))

		print("\nNormierter Wert:")
		print(erzeuger.normiert.get_row(datum))

		# Test zum plotten
		# import matplotlib.pyplot as plt
		#
		# current_erzeuger_art = ErzeugerArt.Photovoltaik
		# tag = "2024-07-01"
		#
		# df = smard.get_erzeuger(current_erzeuger_art).verbrauch_realisiert.df
		# df_am_tag = df[df["Datum von"].dt.date == pd.to_datetime(tag).date()]
		#
		# plt.figure(figsize=(10, 5))
		# plt.plot(df_am_tag["Datum von"], df_am_tag[current_erzeuger_art], marker=".")
		# plt.xlabel("Zeit")
		# plt.ylabel(f"{current_erzeuger_art} (MW)")
		# plt.title(f"{current_erzeuger_art} über die Zeit")
		# plt.grid(True)
		# plt.show()
