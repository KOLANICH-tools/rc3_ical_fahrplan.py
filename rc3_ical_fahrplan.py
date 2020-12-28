import sys
from datetime import datetime, timedelta
from pathlib import Path

import dateutil.parser
import html2markdown
import pytz
from bs4 import BeautifulSoup
from icalendar import Calendar, Event, vText

try:
	import ujson as json
except ImportError:
	import json

def parseTimeDeltaStr(s):
	(h, m, s) = [int(e) for e in s.split(":")]
	return timedelta(seconds=s, minutes=m, hours=h)


fahrplanURI = "https://rc3.world/rc3/public_fahrplan"

def convertFahrplan(parsedHTML: BeautifulSoup) -> Calendar:
	events = []
	congressTimeZone = pytz.timezone("Europe/Berlin")

	for el in parsedHTML.select("script[type='application/json']"):
		ej = json.loads(el.text)
		startT = ej["schedule_start"].replace("noon", "12:00:00").replace("midnight", "00:00:00")
		startT = dateutil.parser.parse(startT).replace(tzinfo=congressTimeZone)
		duration = parseTimeDeltaStr(ej["schedule_duration"])
		descriptionText = html2markdown.convert(ej["description_html"])
		evt = Event()
		evt.add("uid", el["id"] + "@frab.cccv.de")
		speakers = ej["speakers"].split(", ")
		# for s in speakers:
		# 	evt.add("attendee;CN=" + ''.join(e for e in s if e.isalnum()), "")
		evt.add("summary", "[" + ej["language"] + "] " + ej["title"] + "; " + ej["speakers"])
		evt.add("description", ej["track_name"] + "\n" + descriptionText)
		evt.add("location", ej["room_name"])
		evt.add("DTSTART", startT)
		evt.add("DTEND", startT + duration)
		evt.add("name", "[" + ej["language"] + "]" + ej["title"])
		events.append(evt)

	cal = Calendar()

	for evt in events:
		cal.add_component(evt)
	cal["summary"] = "Remote Congress Experience"

	return cal

def main():
	if len(sys.argv) > 2:
		outFile = sys.argv[1]
	else:
		outFile = "./public_fahrplan.ical"

	if len(sys.argv) > 3:
		inputFile = sys.argv[2]
	else:
		inputFile = "./public_fahrplan.html"

	outFile = Path(outFile)
	inputFile = Path(inputFile)

	if inputFile.is_file():
		inputSource = inputFile.read_text(encoding="utf-8")
	else:
		import requests

		inputSource = requests.get(fahrplanURI).text
		inputFile.write_text(inputSource, encoding="utf-8")

	outFile.write_bytes(convertFahrplan(BeautifulSoup(inputSource, "html5lib")).to_ical())


if __name__ == "__main__":
	main()
