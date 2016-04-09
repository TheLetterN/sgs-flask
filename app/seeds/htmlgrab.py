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

import datetime
import json
import os
import sys
from collections import OrderedDict
import requests
from bs4 import BeautifulSoup, SoupStrainer
from flask import current_app
from werkzeug import secure_filename

from app import db
from app.seeds.models import (
    dbify,
    BotanicalName,
    CommonName,
    Cultivar,
    Image,
    Packet,
    Series,
    row_exists
)


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
        cn['common name'] = dbify(header.h1.text.lower().replace('seeds', ''))
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
            srd['series name'] = dbify(sr.find(text=True, recursive=False)
                                       .lower().replace(' series', ''))
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
            cv['cultivar name'] = dbify(cv_div.h3.find(text=True,
                                                       recursive=False))
            thumb = cv_div.img['src']
            if thumb[0] == '/':  # Damn you, relative paths!
                thumb = 'http://www.swallowtailgardenseeds.com' + thumb
            elif 'http' not in thumb:
                thumb = 'http://www.swallowtailgardenseeds.com/' + thumb
            cv['thumbnail'] = thumb
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
                if sr['series name'].lower() in cv['cultivar name'].lower():
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
        tree: A dictionary of data as generated by `Page.tree` with
            common name as the outermost dictionary.
        index: The `Index` to add the `tree` data to.
    """
    def __init__(self, tree, index):
        self.tree = tree
        self.index = index

    @classmethod
    def from_json(cls, json_data, **kwargs):
        """Construct a `PageAdder` instance from a `json` string.

        Args:
            json_data: A JSON string to load data from.
        """
        return cls(json.loads(json_data), **kwargs)

    @classmethod
    def from_json_file(cls, filename, **kwargs):
        """Construct a `PageAdder` instance from a JSON file.

        Args:
            filename: The name of the JSON file to load.
        """
        with open(filename, 'r') as inf:
            return cls.from_json(inf.read(), **kwargs)

    @staticmethod
    def _generate_cultivars(cn, cv_dicts, stream=sys.stdout):
        """Generate cultivars to save to the database.

        Args:
            cn: The `CommonName` the cultivars will belong to.
            cv_dicts: A list of dicts containing `Cultivar` data.

        Yields:
            Cultivar: A generated `Cultivar`.
        """
        for cvd in cv_dicts:
            cv_name = cvd['cultivar name']
            if 'thumbnail' in cvd:
                cv_thumb = cvd['thumbnail']
            else:
                cv_thumb = None
            if 'botanical name' in cvd:
                cv_bn = cvd['botanical_name']
            else:
                cv_bn = None
            if 'description' in cvd:
                cv_desc = cvd['description']
            else:
                cv_desc = None
            cv_pkts = []
            if 'packet' in cvd:
                cv_pkts.append(cvd['packet'])
            if 'jumbo' in cvd:
                cv_pkts.append(cvd['jumbo'])
            cv = Cultivar.get_or_create(name=cv_name,
                                        common_name=cn.name,
                                        index=cn.index.name,
                                        stream=stream)
            if cv_thumb:
                thumb = Thumbnail(cv_thumb)
                if not cv.thumbnail or thumb.filename != cv.thumbnail.filename:
                    cv.thumbnail = thumb.save()
                    print('Thumbnail for \'{0}\' set to \'{1}\'.'
                          .format(cv.fullname, thumb.filename), file=stream)
            if cv_bn:
                bn = BotanicalName.get_or_create(name=cv_bn,
                                                 stream=stream,
                                                 fix_bad=True)
                if bn not in cn.botanical_names:
                    cn.botanical_names.append(bn)
                    print('Added BotanicalName \'{0}\' to \'{1}\'.'
                          .format(bn.name, cn.name), file=stream)
                cv.botanical_name = bn
            if cv_desc and cv.description != cv_desc:
                cv.description = cv_desc
                print('Description for \'{0}\' set to: {1}'
                      .format(cv.fullname, cv.description), file=stream)
            if cv_pkts:
                for cv_pkt in cv_pkts:
                    sku = cv_pkt['sku']
                    price = cv_pkt['price']
                    qty = cv_pkt['quantity']
                    units = cv_pkt['units']
                    pkt = Packet.query.filter(Packet.sku == sku).one_or_none()
                    if pkt and pkt.cultivar and pkt.cultivar is not cv:
                        print('WARNING: The packet for \'{0}\' with the '
                              'SKU \'{1}\' was not added because another '
                              'packet already exists with the same SKU!'
                              .format(cv.fullname, pkt.sku), file=stream)
                        pkt = None
                    else:
                        pkt = Packet.from_values(sku=sku,
                                                 price=price,
                                                 quantity=qty,
                                                 units=units)
                    if pkt:
                        cv.packets.append(pkt)
                        print('Packet \'{0}\' added to \'{1}\'.'
                              .format(pkt.info, cv.fullname), file=stream)
            yield cv

    def save(self, stream=sys.stdout):
        """Save all information to the database."""
        cn_name = self.tree['common name']
        if 'synonyms' in self.tree:
            cn_synonyms = self.tree['synonyms']
        else:
            cn_synonyms = None
        if 'description' in self.tree:
            cn_desc = self.tree['description']
        else:
            cn_desc = None
        if 'instructions' in self.tree:
            cn_inst = self.tree['instructions']
        else:
            cn_inst = None
        cn = CommonName.get_or_create(name=cn_name,
                                      index=self.index.name,
                                      stream=stream)
        if cn.created:
            db.session.add(cn)
        if cn_synonyms and cn.synonyms_string != cn_synonyms:
            cn.synonyms_string = cn_synonyms
            print('Synonyms for \'{0}\' set to: {1}.'
                  .format(cn.name, cn.synonyms_string), file=stream)
        if cn_desc and cn.description != cn_desc:
            cn.description = cn_desc
            print('Description for \'{0}\' set to: {1}'
                  .format(cn.name, cn.description), file=stream)
        if cn_inst and cn.instructions != cn_inst:
            cn.instructions = cn_inst
            print('Planting instructions for \'{0}\' set to: {1}'
                  .format(cn.name, cn.instructions), file=stream)

        if 'botanical names' in self.tree:
            bn_names = self.tree['botanical names']
            for bn_name in bn_names:
                bn = BotanicalName.get_or_create(bn_name,
                                                 stream=stream,
                                                 fix_bad=True)
                if bn not in cn.botanical_names:
                    cn.botanical_names.append(bn)
                    print('Botanical name \'{0}\' added to \'{1}\'.'
                          .format(bn.name, cn.name), file=stream)
        if 'series' in self.tree:
            srds = self.tree['series']
            for srd in srds:
                sr_name = srd['series name']
                if 'description' in srd:
                    sr_desc = srd['description']
                else:
                    sr_desc = None
                sr = Series.get_or_create(name=sr_name,
                                          common_name=cn.name,
                                          index=self.index.name)
                if sr_desc and sr.description != sr_desc:
                    sr.description = sr_desc
                    print('Description for \'{0}\' set to: {1}'
                          .format(sr.name, sr.description), file=stream)
                if sr.common_name is not cn:
                    sr.common_name = cn
                    print('The Series \'{0}\' has been added to \'{1}\'.'
                          .format(sr.name, cn.name), file=stream)

                if 'cultivars' in srd:
                    sr_cvds = srd['cultivars']
                    for cv in self._generate_cultivars(cn=cn,
                                                       cv_dicts=sr_cvds,
                                                       stream=stream):
                        if cv not in sr.cultivars:
                            sr.cultivars.append(cv)
                            print('Cultivar \'{0}\' added to Series \'{1}\'.'
                                  .format(cv.fullname, sr.fullname),
                                  file=stream)
        if 'cultivars' in self.tree:
            for cv in self._generate_cultivars(cn=cn,
                                               cv_dicts=self.tree['cultivars'],
                                               stream=stream):
                print('Cultivar \'{0}\' added to CommonName \'{1}\'.'
                      .format(cv.fullname, cn.name), file=stream)
        db.session.commit()


class Thumbnail(object):
    """Class for handling thumbnail images."""
    def __init__(self, url):
        self.url = url
        self.directory = current_app.config.get('IMAGES_FOLDER')

    @property
    def filename(self):
        """str: The filename of the thumbnail image."""
        return secure_filename(os.path.split(self.url)[-1])

    @property
    def savepath(self):
        """str: The full path to where the file will be saved."""
        return os.path.join(self.directory, self.filename)

    def download(self):
        """Download thumbnail image."""
        img = requests.get(self.url)
        if img.status_code == 200:
            with open(self.savepath, 'wb') as outf:
                outf.write(img.content)
        else:
            img.raise_from_status()

    def exists(self):
        """Check if file exists already."""
        return os.path.exists(self.fullpath)

    def save(self):
        """Save thumbnail as `parent.thumbnail` and add to images.

        Returns:
            Image: The `Image` to be set as a thumbnail.
        """
        if row_exists(Image.filename, self.filename):
            now = datetime.datetime.now().strftime('%m-%d-%Y_at_%H-%M-%S')
            parts = os.path.splitext(self.filename)
            self.filename = parts[0] + now + parts[1]
            if row_exists(Image.name, self.filename):
                raise RuntimeError('Attempt to rename thumbnail failed, as an '
                                   'image named \'{0}\' already exists!'
                                   .format(self.filename))
        self.download()
        return Image(filename=self.filename)
