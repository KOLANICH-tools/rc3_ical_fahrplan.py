#!/usr/bin/env python3

import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
	import ujson as json
except ImportError:
	import json

rooms = {
	"cbase": "c-base",
	"cwtv": "Chaos-West TV",
	"r3s": "Remote Rhein Ruhr Stage",
	"csh": "ChaosStudio Hamburg",
	"chaoszone": "ChaosZone TV",
	"fem": "FeM",
	"franconiannet": "franconian.net",
	"aboutfuture": "about:future",
	"sendezentrum": "Sendezentrum",
	"haecksen": "Haecksen",
	"gehacktes": "Gehacktes from Hell / Bierscheune",
	"xhain": "xHain Lichtung",
	"infobeamer": "Infobeamer"
}

BASE = "https://live.dus.c3voc.de/"

resolutions = {
	"hd": "hd",
	"sd": "sd",
	"audio": "segment"
}

formats = {
	"HLS": ("hls", "m3u8"),
	"WebM": ("webm", "webm")
}

translations = {
	"native": "Native",
	"translated": "Translated",
	"translated-2": "Translated 2"
}

def main() -> None:
	curDir = Path(".").absolute()
	for formatName, formatDescriptor in formats.items():
		formatDir, ext = formatDescriptor
		for resolution in resolutions:
			formatResFile = curDir / ("rc3_" + formatDir + "_" + resolution + ".m3u")

			with formatResFile.open("wt") as f:
				for roomSlug, roomName in rooms.items():
					prefix = BASE + formatDir + "/" + roomSlug + "/"
					for translSlug, translName in translations.items():
						resUri = prefix + translSlug + "_" + resolution + "." + ext

						print(file=f)
						print("#EXTINF:-1, " + roomName + " " + translName, file=f)
						print(resUri, file=f)

if __name__ == "__main__":
	main()
