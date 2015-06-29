#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# A little python-script that produces automatically the weekly needed
# calendar for the UWR.
# (see http://wiki.ubuntuusers.de/ubuntuusers/Ikhayateam/UWR)
#
# Version 1.5 (2014-03-16)
# written by chris34 (http://ubuntuusers.de/user/chris34/)
#
# licensed under the
#
##            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
##                    Version 2, December 2004
##
## Copyright (C) 2004 Sam Hocevar <sam@hocevar.net>
##
## Everyone is permitted to copy and distribute verbatim or modified
## copies of this license document, and changing it is allowed as long
## as the name is changed.
##
##            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
##   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
##
##  0. You just DO WHAT THE FUCK YOU WANT TO.

import datetime
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint
from re import sub
import sys
import time
import urllib2


class uuCalendarMonthOverviewParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        self.calendar_table = False

        self.parsed_urls = []

    def handle_starttag(self, tag, attrs):
        if tag == u"table" and attrs[0][1] == u"calendar_month":
            self.calendar_table = True

        if self.calendar_table and tag == u"a" and attrs[-1][1] == u"event_link":
            self.parsed_urls.append(attrs[0][1])

    def get_parsed_urls(self):
        return self.parsed_urls

class uuCalendarEventParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        self.event_data = {"name":  "", # h3 without any attribute
                           "ort":   "", # span with class="location"
                           "datum": "", # from table class="vevent" -> tbody -> first tr -> second td; allerdings z.B. von Juli 3, 2013 19:30 bis Juli 3, 2013 22:00
                          }
        self.name_found = False
        self.ort_found = False
        self.datum_table_found = False
        self.datum_table_tr_counter = 0
        self.datum_found = False

    def _convert_entity(self, string):
        return unichr(name2codepoint[string])

    def _convert_charref(self, string):
        if string[0] == "x":
            return chr(int(string[1:], 16))
        else:
            return chr(int(string))

    def _prepare_name(self):
        name_string = self.event_data["name"][len("Veranstaltung")+1:]
        name_string = name_string.replace(u"„", u"") # remove „
        name_string = name_string.replace(u"“", u"") # remove ”
        self.event_data["name"] = name_string

    def _prepare_datum(self, data):
        '''extracts the beginning of the event'''
        datum = sub(r"\s+", " ", data)

        if u"bis" in datum:
            datum = datum[:datum.index(u"bis")]

        if u"morgen" in datum:
            time_start = datum.index(u"morgen") + len(u"morgen") + 1 # 1 → whitespace
            time_end = time_start + 5 # f.e. 19:00
            time = datum[time_start:time_end]

            time_str = time.split(u":")

            try:
                time = datetime.time(int(time_str[0]), int(time_str[1]))
                datum_obj = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(1), time)
            except ValueError:
                datum_obj = datetime.date.today() + datetime.timedelta(1)

        elif u"heute" in datum or u"gestern" in datum:
            # only parsed but (hopefully) never in output
            datum_obj = datetime.datetime.now()
        else:
            # month strings (2013-10-21)
            to_replace = (
            (u"\n", ""),
            (u"Januar", 1),
            (u"Februar", 2),
            (u"März", 3),
            (u"April", 4),
            (u"Mai", 5),
            (u"Juni", 6),
            (u"Juli", 7),
            (u"August", 8),
            (u"September", 9),
            (u"Oktober", 10),
            (u"November", 11),
            (u"Dezember", 12),
            )

            for i in to_replace:
                datum = datum.replace(i[0], str(i[1]))

            datum = datum[5:-1]
            try:
                datum_obj = datetime.datetime.strptime(datum, "%d. %m %Y %H:%M")
            except ValueError:
                datum_obj = datetime.datetime.strptime(datum, "%d. %m %Y")

        return datum_obj

    def _prepare_ort(self):
        ort = self.event_data["ort"]
        ort = sub(r"\s+", " ", ort)
        ort = ort.replace("\n", "")

        self.event_data["ort"] = ort.strip()

    def handle_starttag(self, tag, attrs):
        # event-name detection
        if tag == u"h3" and len(attrs) == 0:
            self.name_found = True

        # Ort detection
        if tag == u"td" and self.datum_table_tr_counter == 2:
            self.ort_found = True

        # datum detection
        # from table class="vevent" -> tbody -> first tr -> second td
        # f.e. von Juli 3, 2013 19:30 bis Juli 3, 2013 22:00
        if tag == u"table" and len(attrs) > 0:
            if u"vevent" in attrs[0][1]:
                self.datum_table_found = True

        if self.datum_table_found and tag == u"tr":
            self.datum_table_tr_counter += 1

        if self.datum_table_tr_counter == 1 and tag == u"td":
            self.datum_found = True

    def handle_data(self, data):
        if self.name_found:
            self.event_data["name"] += data

        if self.ort_found and data != "":
            self.event_data["ort"] += data

        if self.datum_found:
            self.event_data["datum"] = self._prepare_datum(data)

    def handle_endtag(self, tag):
        if tag == u"h3" and self.name_found:
            self.name_found = False

        if (tag == u"span" or tag == u"td") and self.ort_found:
            self.ort_found = False

        if tag == u"table":
            self.datum_table_found = False

        if self.datum_found and tag == u"td":
            self.datum_found = False

    def get_parsed_data(self):
        self._prepare_ort()
        self._prepare_name()

        return self.event_data

    def handle_entityref(self, name):
        if self.name_found:
            self.event_data["name"] += self._convert_entity(name)

        if self.ort_found:
            self.event_data["ort"] += self._convert_entity(name)

    def handle_charref(self, name):
        if self.name_found:
            self.event_data["name"] += self._convert_charref(name)

        if self.ort_found:
            self.event_data["ort"] += self._convert_charref(name)

def generate_url(date_obj):
    url_base = "http://ubuntuusers.de/calendar"
    sep = "/"
    year = str(date_obj.year)
    month = str(date_obj.month)
    return sep.join([url_base, year, month])

def download_page(url):
    response = urllib2.urlopen(url).read()
    return unicode(response, "utf-8")

def collect_information(pages):
    info_array = pages

    for i in range(0, len(info_array)):
        parser = uuCalendarEventParser()
        parser.feed(download_page(info_array[i]))
        event_data = parser.get_parsed_data()

        info_array[i] = {
            "url":   info_array[i],
            "name":  event_data["name"],
            "ort":   event_data["ort"],
            "datum": event_data["datum"],
            }

    return info_array

def delete_unused_unichr(text):
    '''Some unicode-characters caused an invalid RSS-Feed. Thus, they will be filtered/deleted.

    characters in detail: decimal 0-31, 127-159; see http://unicode-table.com/ for more information
    '''
    new_text = text

    unused_unichr_range = range(0, 32)
    unused_unichr_range.extend(range(127, 160))

    for chr_code in unused_unichr_range:
        new_text = new_text.replace(unichr(chr_code), "")

    return new_text

def main(date=None):
    if date == None:
        today = datetime.date.today()
    else:
        today = date

    # find next Tuesday
    if today.weekday() == 0:
        calendar_begin = today + datetime.timedelta(1)
    else:
        calendar_begin = today + datetime.timedelta(8-today.weekday())

    calendar_end = calendar_begin + datetime.timedelta(13)

    month_pages = [ [generate_url(calendar_begin)],
                    [generate_url(calendar_end)],
                  ]

    if month_pages[0][0] == month_pages[1][0]:
        month_pages.pop(-1)

    pages = []

    for i in month_pages:
        parser = uuCalendarMonthOverviewParser()
        parser.feed(download_page(i[0]))
        pages.extend(parser.get_parsed_urls())

    infos = collect_information(pages)

    # correct date for events that last for more than one day
    duplicate = []

    for i in infos:
        if infos.count(i) > 1 and i not in duplicate:
            duplicate.append(i)

    for e in duplicate:
        duplicateIndex = 0
        for i in infos:
            if e["url"] == i["url"]:
                i["datum"] += datetime.timedelta(duplicateIndex)
                duplicateIndex += 1

    ## create_table
    table = """## generated on %s
{{{#!vorlage Tabelle
<-4 rowclass="titel"-4> Termine vom %s bis %s
+++
<rowclass="kopf">Name
Ort
Datum
Uhrzeit
""" %( datetime.datetime.today().ctime(),
       calendar_begin.strftime("%d.%m.%Y"),
       calendar_end.strftime("%d.%m.%Y")
     )

    highlight = False

    for i in infos:
        if  calendar_end >= i["datum"].date() >= calendar_begin:
            table += u"+++\n"

            name = delete_unused_unichr(i["name"])
            ort = delete_unused_unichr(i["ort"])

            ordered_infos = [ "[calendar:" + i["url"][32:-1] + ":" + name + u"]",
                             ort,
                             i["datum"].strftime("%a, %d.%m.%Y\n%H:%M") + u" Uhr"]

            if highlight: # highlight every second row
                ordered_infos[0] = u'<rowclass="highlight">' + ordered_infos[0]
            highlight = not(highlight)

            table += u"\n".join(ordered_infos) + u"\n"

    table += u"}}}"

    print table

if __name__ == "__main__":
    import locale
    locale.setlocale(locale.LC_ALL, "")

    main()
