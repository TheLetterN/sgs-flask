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

import os
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
        unwanted = ['\r', '\t', '\xa0']
    for u in unwanted:
        text = text.replace(u, '')
    return text


# <p> functions
def merge_p(p_tags):
    """Merge a list of paragraphs into a single block of text."""
    return '\n'.join(str(p) for p in p_tags)


def strip_p(p):
    """Strip outermost <p> tag from a string containing it."""
    if p[:2].lower() == '<p' and p[-4:].lower() == '</p>':
        return p[p.index('>') + 1:-4].strip()
    else:
        print(p)#TMP
        raise ValueError('p must begin with <p> and end with </p>! p = {0}'
                         .format(p))


def format_p(p):
    """Format a string containing one or more <p> block for database storage.

    Args:
        p: The string to format.

    Returns:
        str: The formatted string.
    """
    try:
        p = strip_p(p)
    except ValueError:
        pass
    p = clean(p)
    return p

class Page(object):
    """Class for page to draw data from.
    
    Attributes:
        soup: A `BeautifulSoup` object generated from text HTML.
    """
    def __init__(self, text, parser=None):
        if not parser:
            parser = 'html.parser'
        self.soup = BeautifulSoup(text, parser)

    @staticmethod
    def download_image(url, path=None):
        """Download a given image if it exists.

        Args:
            url: The URL to download the image from.
            path: An optional path to the directory to save the image to. If
                no path is given, it will default to the current working
                directory.

        Raises:
            HTTPError: If the image could not be downloaded.
        """
        if not path:
            path = os.getcwd()
        filename = secure_filename(os.path.split(url)[-1])
        fullpath = os.path.join(path, filename)
        img = requests.get(url)
        if img.status_code == 200:
            with open(fullpath, 'wb') as outf:
                outf.write(img.content)
        else:
            img.raise_for_status()

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
        qty = ' '.join(qty_parts)
        units = ' '.join(units_parts)
        return {'price': price, 'quantity': qty, 'units': units}

    
    @classmethod
    def from_url(cls, url):
        """Scrape a URL to get text for constructing a new `Page`."""
        text = requests.get(url).text
        return cls(text)

    def get_common_name(self):
        """Get a dict containing `CommonName` data from page.
        
        Returns:
            dict: Common name data.
        """
        header = self.soup.header
        cn = dict()
        cn['name'] = dbify(header.h1.text.lower().replace('seeds', '').strip())
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
        desc_strainer = SoupStrainer(class_='intro')
        desc_divs = self.soup.find_all(desc_strainer)
        if desc_divs:
            desc_div = desc_divs[0]
            cn['description'] = format_p(merge_p(desc_div.find_all('p')))
        inst_strainer = SoupStrainer(class_='growing')
        inst_divs = self.soup.find_all(inst_strainer)
        if inst_divs:
            inst_div = inst_divs[0]
            cn['instructions'] = format_p(merge_p(inst_div.find_all('p')))
        return cn

    def get_cultivars(self):
        """Get a list of `dict` objects containing `Cultivar` data."""
        cv_strainer = SoupStrainer(name='div', class_='cultivar')
        cv_divs = self.soup.find_all(cv_strainer)
        cultivars = []
        for cv_div in cv_divs:
            cv = dict()
            cv_div.h3.em.decompose()  # Remove common name, we don't need it.
            if cv_div.h3.em:  # Second em = botanical name if present.
                cv['botanical name'] = cv_div.h3.em.text.strip()
                cv_div.h3.em.decompose()
            cv['name'] = dbify(cv_div.h3.text.strip())
            if cv_div.p:
                desc = format_p(merge_p(cv_div.find_all('p')))
                cv['description'] = desc.strip()
            cv['thumbnail'] = cv_div.img['src']
            pkt_tds = cv_div.find_all('td')
            cv['packet'] = self._str_to_packet(pkt_tds[0].text)
            cv['packet']['sku'] = cv_div.small.text
            if len(pkt_tds) == 2:  # Should indicate presence of jumbo packet.
                cv['jumbo'] = self._str_to_packet(pkt_tds[1].text)
                cv['jumbo']['sku'] = cv_div.small.text + 'J'
            cultivars.append(cv)
        return cultivars
