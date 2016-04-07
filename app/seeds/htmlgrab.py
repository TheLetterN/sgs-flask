# -*- coding: utf-8 -*-
# This file is part of SGS-Flask.

# SGS-Flask is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SGS-Flask is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright Swallowtail Garden Seeds, Inc


"""
    sgs-flask.app.seeds.htmlgrab

    This module is for grabbing data from the existing Swallowtail Garden
    Seeds website and using it to populate sgs-flask.
"""

import json
import os
from collections import OrderedDict
import requests
from bs4 import BeautifulSoup, SoupStrainer
from flask import current_app
from werkzeug import secure_filename

from app.seeds.models import dbify


def clean(text, unwanted=None):
    """Remove unwanted characters/substrings from a block of text.
    
    Returns:
        str: Cleaned up version of `text`.
    """
    if not unwanted:
        unwanted = ['\r', '\t']
    for u in unwanted:
        text = text.replace(u, '')
    text = text.replace('\xa0', ' ')
    return text.strip()


def merge_p(p_tags):
    """Merge a list of paragraphs into a single block of text."""
    return '\n'.join(str(p) for p in p_tags)


class Page(object):
    """Class for page to draw data from.
    
    Attributes:
        soup: A `BeautifulSoup` object generated from text HTML.
    """
    def __init__(self, text, parser=None):
        if not parser:
            parser = 'html.parser'
        text = clean(text)
        self.soup = BeautifulSoup(text, parser)
    
    @classmethod
    def from_url(cls, url):
        """Scrape a URL to get text for constructing a new `Page`."""
        text = requests.get(url).text
        return cls(text)

    @property
    def common_name(self):
        """OrderedDict: `CommonName` data from page header."""
        header = self.soup.header
        cn = OrderedDict()
        cn['name'] = dbify(header.h1.text.lower().replace('seeds', ''))
        if header.h2:
            cn['synonyms'] = header.h2.text.strip()
        botanical_names = []
        if header.h3:
            bns_str = header.h3.text.strip()
            if ', ' not in bns_str:
                botanical_names = [bns_str]
            else:
                bns = bns_str.split(', ')
                abbreviations = dict()
                for bn in bns:
                    parts = bn.split(' ')
                    genus = parts[0]
                    if len(genus) > 2:
                        abbr = genus[0] + '.'
                        if abbr not in abbreviations:
                            abbreviations[abbr] == genus
                    elif genus in abbreviations:
                        bn = ' '.join([abbreviations[genus]] + parts[1:])
                    botanical_names.append(bn)
            cn['botanical names'] = botanical_names
        desc_divs = self.soup.find_all(class_='intro')
        if desc_divs:
            desc_div = desc_divs[0]
            ps = desc_div.find_all('p')
            cn['description'] = merge_p(ps)
        inst_divs = self.soup.find_all(class_='growing')
        if inst_divs:
            inst_div = inst_divs[0]
            cn['instructions'] = merge_p(inst_div.find_all('p'))
        return cn

    @property
    def series(self):
        """list: A list of `OrderedDict` objects with `Series` data."""
        srs_raw = self.soup.find_all(id=lambda x: x and 'series' in x.lower())
        # Some series headers are in divs, some just have h2s, but the
        # pattern <h2>series</h2><p>description</p> holds in both cases.
        srs = [sr.h2 if sr.h2 else sr for sr in srs_raw]
        series = []
        for sr in srs:
            srd = OrderedDict()
            srd['name'] = dbify(sr.find(text=True, recursive=False).lower().replace(' series', ''))
            ps = sr.find_next_siblings('p')
            if ps:
                srd['description'] = merge_p(ps)
            series.append(srd)
        return series

    @property
    def cultivars(self):
        """list: A list of `OrderedDict` objects with `Cultivar` data."""
        cv_strainer = SoupStrainer(name='div', class_='cultivar')
        cv_divs = self.soup.find_all(cv_strainer)
        cultivars = []
        for cv_div in cv_divs:
            cv = OrderedDict()
            cv['name'] = dbify(cv_div.h3.find(text=True, recursive=False))
            cv['thumbnail'] = cv_div.img['src']
            ems = cv_div.h3.find_all('em')
            if len(ems) == 2:
                cv['botanical name'] = ems[1].text.strip()
            ps = cv_div.h3.find_next_siblings('p')
            if ps:
                desc = merge_p(ps)
                cv['description'] = desc.strip()
            pkt_tds = cv_div.find_all('td')
            cv['packet'] = self._str_to_packet(pkt_tds[0].text)
            cv['packet']['sku'] = cv_div.small.text
            cv['packet'].move_to_end('sku', last=False)
            if len(pkt_tds) == 2:  # Should indicate presence of jumbo packet.
                cv['jumbo'] = self._str_to_packet(pkt_tds[1].text)
                cv['jumbo']['sku'] = cv_div.small.text + 'J'
            cultivars.append(cv)
        return cultivars

    @property
    def tree(self):
        """OrderedDict: A tree of all data with `common_name` as the root."""
        cn = self.common_name
        cn['series'] = self.series
        cvs = self.cultivars
        for sr in cn['series']:
            for cv in list(cvs):
                if sr['name'].lower() in cv['name'].lower():
                    if 'cultivars' not in sr:
                        sr['cultivars'] = [cvs.pop(cvs.index(cv))]
                    else:
                        sr['cultivars'].append(cvs.pop(cvs.index(cv)))
        cn['cultivars'] = cvs
        return cn

    @property
    def json(self):
        """str: JSONified version of `tree`."""
        return json.dumps(self.tree, indent=4)

    @staticmethod
    def _str_to_packet(pkt_str):
        """Split a string of packet data into price, quantity, and units.

        Note:
            Packet strings are in the format:

            '<quantity> <units> - <price>'

            e.g.:

            '100 seeds - $1.99'

        Returns:
            dict: The price, quantity, and units of the packet.
        """
        parts = pkt_str.strip().split(' - ')
        qty_and_units = parts[0]
        raw_price = parts[1]
        price = raw_price.strip('$')
        qau_parts = qty_and_units.split(' ')
        qty_parts = []
        units_parts = []
        for part in qau_parts:
            if part.isalpha():
                units_parts.append(part)
            else:
                qty_parts.append(part)
        qty = ' '.join(qty_parts).replace(',', '')
        units = ' '.join(units_parts)
        pkt = OrderedDict()
        pkt['price'] = price
        pkt['quantity'] = qty
        pkt['units'] = units
        return pkt

    def save_json(self, filename):
        """Save JSON string to a file."""
        with open(filename, 'w') as outf:
            outf.write(self.json)


class PageAdder(object):
    """Class for adding `Page.tree` data to the site/db.

    Note:
        Since there will be times when `Page` gets the scraped data wrong,
        JSON data generated by it must be checked before being used to
        populate the site. As such, `PageAdder` is distinct from `Page`.
    
    Attributes:
        data: A dictionary of data as generated by `Page.tree`.
    """
    def __init__(self, data):
        self.data = data

    @classmethod
    def from_json(cls, json_data):
        """Construct a `PageAdder` instance from a `json` string.

        Args:
            json_data: A JSON string to load data from.
        """
        return cls(json.loads(json_data))

    @classmethod
    def from_json_file(cls, filename):
        """Construct a `PageAdder` instance from a JSON file.

        Args:
            filename: The name of the JSON file to load.
        """
        with open(filename, 'r') as inf:
            return cls.from_json(inf.read())


class Thumbnail(object):
    """Class for handling thumbnail images."""
    def __init__(self, url):
        self.url = url
        self.directory = current_app.config.get('IMAGES_FOLDER')

    @property
    def filename(self):
        """str: The filename of the thumbnail image."""
        return secure_filename(os.path.split(url)[-1])

    @property
    def savepath(self):
        """str: The full path to where the file will be saved."""
        return os.path.join(self.directory, self.filename)

    def download(self):
        """Download thumbnail image."""
        img = requests.get(url)
        if img.status_code == 200:
            with open(self.savepath, 'wb') as outf:
                outf.write(img.content)
        else:
            img.raise_from_status()

    def exists(self):
        """Check if file exists already."""
        return os.path.exists(self.fullpath)

    def save(self, parent):
        """Save thumbnail as `parent.thumbnail` and add to images.

        Args:
            parent: A database model with a `thumbnail` column.
        """
        if self.exists():
            raise FileExistsError('The image \'{0}\' already exists!'
                                  .format(self.filename))
        img = Image.query.filter(Image.filename == filename).one_or_none()
        if img:
            raise RuntimeError('There is already an Image named \'{0}\' in '
                               'the database, but the file it is associated '
                               'with doesn\'t exist! This should never '
                               'happen, so there is either a bug where Image '
                               'is being manipulated, or some idiot deleted '
                               'the image without removing its db entry.'
                               .format(self.filename))
        parent.thumbnail = Image(filename=self.filename)
        self.download()
