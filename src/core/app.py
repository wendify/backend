from datetime import datetime
import logging

from core.setup.smard import Smard
from core.erzeugerArt import ErzeugerArt


class App:
	def __init__(self):
		pass

	def run(self):
		logging.info("Starting")

		smard = Smard()

		# Datenreihen für Photovoltaik
		# smard.get_erzeuger(ErzeugerArt.Photovoltaik).verbrauch_realisiert
		# smard.get_erzeuger(ErzeugerArt.Photovoltaik).verbrauch_installiert
		gesuchtes_datum = datetime(2024, 1, 2, 12, 30)
		print("\nRealisierter Wert:\n", smard.get_erzeuger(ErzeugerArt.Photovoltaik).verbrauch_realisiert.get_value_by_datetime(gesuchtes_datum))
		print("\nInstallierter Wert:\n", smard.get_erzeuger(ErzeugerArt.Photovoltaik).e_norm.get_value_by_datetime(gesuchtes_datum))



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
