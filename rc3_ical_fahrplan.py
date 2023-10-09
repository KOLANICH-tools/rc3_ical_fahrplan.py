#!/usr/bin/env python3

import sys
import typing
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from warnings import warn

import dateutil.parser
import defusedxml.ElementTree as ET
import html2markdown
import pytz
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from icalendar.cal import Calendar, Event

warn("We have moved from M$ GitHub to https://codeberg.org/KOLANICH-tools/rc3_ical_fahrplan.py , read why on https://codeberg.org/KOLANICH/Fuck-GuanTEEnomo .")

try:
	import mjson as json
except ImportError:
	import json


def parseTimeDeltaStr(s: str) -> timedelta:
	durNums = [int(e) for e in s.split(":")]
	if len(durNums) == 2:
		durNums.append(0)

	(h, m, s) = durNums
	return timedelta(seconds=s, minutes=m, hours=h)


def parsePretalxURI(u: str) -> typing.Tuple[str, str]:
	u = urlparse(u)
	p = u.path.split("/")
	if not p[0]:
		p = p[1:]

	if p[1] == "talk":
		roomSlug = p[0]
		pretalxId = p[2]
		return roomSlug, pretalxId


yearS = str(2021)
fahrplan_HTML_URI = "https://rc3.world/" + yearS + "/public_fahrplan"
fahrplan_PRETALX_XML_URI = "https://static.rc3.world/schedule/everything.xml"  # SCHEDULE_URL from https://github.com/EventFahrplan/EventFahrplan/blob/master/app/build.gradle

PRETALX_DOMAIN = "pretalx.c3voc.de"
PRETALX_BASE = "https://" + PRETALX_DOMAIN + "/"
PRETALX_API_BASE = PRETALX_BASE + "/api"
PRETALX_EVENTS_BASE = PRETALX_API_BASE + "/events"


def getAllSpeakersInfoURI(confSlug):
	return PRETALX_EVENTS_BASE + "/" + confSlug + "/speakers/"


def getAllEvents():
	src = requests.get(PRETALX_EVENTS_BASE).text
	return json.loads(src)


class SpeakerInfoHolder:
	__slots__ = ("speakersInfoFile", "speakersInfo")

	def __init__(self, allConfsSlugs):
		self.speakersInfoFile = Path("./speakers.json")
		self.speakersInfo = {}

		if self.speakersInfoFile.is_file():
			self.speakersInfo = json.loads(speakersInfoFile.read_text(encoding="utf-8"))
		else:
			self.getAllSpeakersInfo(*allConfsSlugs)
			self.speakersInfoFile.write_text(self.speakersInfo, encoding="utf-8")

	def getAllSpeakersInfo(self, *confSlugs):
		import requests

		for confSlug in confSlugs:
			speakersInfoSrc = requests.get(getSpeakerInfoURI(confSlug)).text
			speakerInfo = json.loads(speakersInfoSrc)
			self.speakersInfo[confSlug] = speakerInfo


def getSpeakerInfoURI(confSlug, pretalxId):
	return getAllSpeakersInfoURI(confSlug) + pretalxId + "/"


# API DOCS: https://docs.pretalx.org/api/index.html


class Talk:
	__slots__ = ("title", "language", "times", "track", "room", "description", "abstract", "logo", "subtitle", "persons", "links", "attachments", "iD", "pretalxId", "guid", "_slug", "_roomSlug", "nameSlug", "roomNameSlug")

	def __init__(self, *, title=None, language=None, times=None, track=None, room=None, description=None, abstract=None, logo=None, subtitle=None, persons=None, links=None, attachments=None, iD=None, pretalxId=None, guid=None, slug=None, roomSlug=None, nameSlug=None, roomNameSlug=None) -> None:
		self.language = language
		self.track = track
		self._roomSlug = roomSlug
		self.room = room
		self.description = description
		self.abstract = abstract
		self.logo = logo
		self.subtitle = subtitle
		self.persons = persons
		self.links = links
		self.attachments = attachments
		self.iD = iD
		self.pretalxId = pretalxId
		self.guid = guid
		self._slug = slug
		self.times = times
		self.title = title
		self.nameSlug = nameSlug
		self.roomNameSlug = roomNameSlug

	@property
	def roomSlug(self) -> str:
		if self._roomSlug:
			return self._roomSlug
		else:
			return "rc3-" + yearS + "-" + self.roomNameSlug

	@property
	def slug(self):
		if self._slug:
			return self._slug
		else:
			return self.roomSlug + "-" + self.nameSlug

	@property
	def pretalxUID(self) -> str:
		return "pretalx-" + self.roomSlug + "-" + self.pretalxId + "@" + PRETALX_DOMAIN

	@property
	def frabUID(self):
		return self.guid + "@frab.cccv.de"

	@property
	def pretalxProdid(self) -> str:
		return "-//pretalx//" + PRETALX_DOMAIN + "//" + self.pretalxId

	@property
	def pretalxURI(self):
		return PRETALX_BASE + "rc3-" + yearS + "-" + self.room + "/talk/" + self.pretalxId + "/"


class Backend:
	__slots__ = ()


class HTMLBackend(Backend):
	__slots__ = ("inputFile",)

	def __init__(self, inputFile):
		self.inputFile = inputFile

	def __call__(self) -> typing.Iterator[Event]:
		if self.inputFile.is_file():
			inputSource = self.inputFile.read_text(encoding="utf-8")
		else:
			import requests

			inputSource = requests.get(fahrplan_HTML_URI).text
			self.inputFile.write_text(inputSource, encoding="utf-8")

		return self.parseFahrplan(BeautifulSoup(inputSource, "html5lib"))

	def parseFahrplan(self, parsedHTML: "BeautifulSoup") -> typing.Iterator[Event]:
		congressTimeZone = pytz.timezone("Europe/Berlin")
		for el in parsedHTML.select("script[type='application/json']"):
			ej = json.loads(el.text)
			startT = ej["schedule_start"].replace("noon", "12:00:00").replace("midnight", "00:00:00").replace("Dezember", "Dec")
			startT = dateutil.parser.parse(startT).replace(tzinfo=congressTimeZone)
			duration = parseTimeDeltaStr(ej["schedule_duration"])
			speakers = ej["speakers"].split(", ")
			roomSlug, pretalxId = parsePretalxURI(ej["link"])
			yield Talk(title=ej["title"], language=ej["language"], times=(startT, startT + duration), track=ej["track_name"], room=ej["room_name"], description=ej["description_html"], abstract=ej["abstract"], persons=speakers, guid=el["id"], pretalxId=pretalxId, roomSlug=roomSlug)


class XMLBackend(Backend):
	__slots__ = ("inputFile",)

	def __init__(self, inputFile: Path) -> None:
		self.inputFile = inputFile

	def __call__(self) -> typing.Iterator[Event]:
		if self.inputFile.is_file():
			inputSource = self.inputFile.read_text(encoding="utf-8")
		else:
			import requests

			inputSource = requests.get(fahrplan_PRETALX_XML_URI).text
			self.inputFile.write_text(inputSource, encoding="utf-8")

		return self.parseFahrplan(ET.fromstring(inputSource))

	def parseFahrplan(self, parsedXML: "xml.etree.ElementTree.Element") -> typing.Iterator[Event]:
		# scheduleEl = parsedXML.find('schedule')
		scheduleEl = parsedXML
		c = scheduleEl.find("conference")
		confTitle = c.find("title").text
		confAcr = c.find("acronym").text
		congressTimeZone = pytz.timezone(c.find("time_zone_name").text)
		days = scheduleEl.findall("day")
		for d in days:
			rooms = d.findall("room")
			for r in rooms:
				room_name = r.attrib["name"]
				events = r.findall("event")
				for e in events:
					title = e.find("title").text
					iD = e.attrib["id"]
					language = e.find("language").text
					startT = dateutil.parser.parse(e.find("date").text).replace(tzinfo=congressTimeZone)
					duration = parseTimeDeltaStr(e.find("duration").text)
					track = e.find("track").text
					description = e.find("description").text
					abstract = e.find("abstract").text
					guid = e.attrib["guid"]
					slug = e.find("slug").text

					roomSlugFromURI, pretalxId = parsePretalxURI(e.find("url").text)

					slugParts = slug.split("-")
					eventNameSlug = "-".join(slugParts[len(roomSlugFromURI) + 1 :])

					logo = e.find("logo").text
					typ = e.find("type").text
					subtitle = e.find("subtitle").text

					personsContainer = e.find("persons")
					persons = []
					for p in personsContainer.findall("person"):
						persons.append(p.text)
						p.attrib["id"]

					yield Talk(title=title, language=language, times=(startT, startT + duration), track=track, room=room_name, description=description, abstract=abstract, persons=persons, iD=iD, guid=guid, slug=slug, roomSlug=roomSlugFromURI, nameSlug=eventNameSlug, pretalxId=pretalxId)


def convertFahrplan(eventsIter: typing.Iterator[Event]) -> Calendar:
	calEvents = []

	for el in eventsIter:
		descrCombined = []

		warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning, module="bs4")
		for descrEl in (el.track, el.abstract, el.description):
			if descrEl:
				descrCombined.append(html2markdown.convert(descrEl))

		descrCombined = "\n".join(descrCombined)

		evt = Event()
		evt.add("UID", el.pretalxUID)
		evt.add("PRODID", el.pretalxProdid)
		# for s in el.persons:
		# 	evt.add("ATTENDEE", "", parameters={"ROLE":"CHAIR", "CN": ''.join(e for e in s if e.isalnum() or e == " ")})
		evt.add("summary", "[" + el.language + "] " + el.title + "; " + ", ".join(el.persons))
		evt.add("description", descrCombined)
		evt.add("location", el.room)
		evt.add("DTSTART", el.times[0])
		evt.add("DTEND", el.times[1])
		evt.add("name", "[" + el.language + "]" + el.title)
		calEvents.append(evt)

	cal = Calendar()

	for evt in calEvents:
		cal.add_component(evt)
	cal["summary"] = "Remote Congress Experience"

	return cal


def main() -> None:
	if len(sys.argv) > 2:
		outFile = sys.argv[1]
	else:
		outFile = "./public_fahrplan.ical"

	if len(sys.argv) > 3:
		inputFile = sys.argv[2]
	else:
		inputFile = "./public_fahrplan.xml"

	outFile = Path(outFile)
	inputFile = Path(inputFile)

	if inputFile.suffix.lower()[1:] == "html":
		b = HTMLBackend(inputFile)
		pass
	elif inputFile.suffix.lower()[1:] == "xml":
		b = XMLBackend(inputFile)
	else:
		raise ValueError("Unknown backend for ext", inputFile.suffix.lower()[1:])

	outFile.write_bytes(convertFahrplan(b()).to_ical())


if __name__ == "__main__":
	main()
