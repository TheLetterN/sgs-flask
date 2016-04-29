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
from bs4 import BeautifulSoup, Comment, Tag
from flask import current_app
from werkzeug import secure_filename

from app import db
from app.seeds.models import (
    dbify,
    BotanicalName,
    Section,
    CommonName,
    Cultivar,
    Image,
    Index,
    Packet,
    Quantity,
    row_exists,
    VegetableData
)


def clean(text, unwanted=None):
    """Remove unwanted characters/substrings from a block of text.

    Returns:
        str: Cleaned up version of `text`.
    """
    FRACTIONS = {
        '&frac14;': '1/4',
        '&frac12;': '1/2',
        '&frac34;': '3/4',
        '&frac18;': '1/8'
    }
    if not unwanted:
        unwanted = ['\r', '\t', '&shy;', '<br>', '<br \>', '</img>']
    for u in unwanted:
        text = text.replace(u, '')
    text = text.replace('\xa0', ' ')
    for f in FRACTIONS:
        text = text.replace(f, FRACTIONS[f])
    return text.strip()


def merge_p(p_tags):
    """Merge a list of paragraphs into a single block of text."""
    return '\n'.join(str(p) for p in p_tags if 'go-to-next' not in str(p))


def get_h_title(tag):
    """Attempt to parse the title in an h1, h2, etc. block."""
    # Remove comments from within h tags, as they screw up tag.contents.
    for t in tag(text=lambda x: isinstance(x, Comment)):
        t.extract()
    try:
        title = next(c for c in tag.contents if hasattr(c, 'isspace')
                     and not c.isspace())
        return title.strip().lower()
    except StopIteration:
        raise RuntimeError('Could not isolate the title in: {0}'.format(tag))


def generate_botanical_names(bns_string):
    """Clean up a string listing multiple botanical names as a header."""
    abbr = dict()
    for bn in bns_string.replace(', syn.', ' syn.').split(', '):
        yield expand_botanical_name(bn, abbr)


def expand_botanical_name(bn, abbreviations):
    """Expand an abbreviated botanical name to its full name.

    Example:

        'D. purpurea' -> 'Digitalis purpurea'

    Args:
        bn: The name to expand into a full botanical name.
        abbreviations: A `dict` containing abbreviations of genuses.

    Returns:
        str: The expanded botanical name.
    """
    parts = bn.replace('syn. ', '').split(' ')
    first = parts[0]
    if len(first) > 2:
        abbr = first[0] + '.'
        if abbr not in abbreviations:
            abbreviations[abbr] = first
    elif first in abbreviations:
        bn = bn.replace(first, abbreviations[first])
    return bn


def cultivar_div_to_dict(cv_div):
    cv = OrderedDict()
    for c in cv_div(text=lambda x: isinstance(x, Comment)):
        c.extract()
    try:
        cv_name = next(
            c for c in cv_div.h3.contents if c and not str(c).isspace()
        )
        if isinstance(cv_name, Tag):
            cv_name = cv_name.text
    except StopIteration:
        cv_name = cv_div.h3.text.strip().split('\n')[0]
    except Exception as e:
        raise RuntimeError('Exception {0} was raised while attempting to work '
                           'on cultivar div: {1}'.format(e, cv_div))
    if not cv_name:
        raise RuntimeError('Could not parse a cultivar name from {0}'
                           .format(cv_div))
    cv['cultivar name'] = dbify(cv_name.replace('\n', ''))
    if 'new for 2016' in cv_div.text.lower():
        cv['new until'] = '12/31/2016'
    if cv_div.img:
        thumb = cv_div.img['src']
        if thumb[0] == '/':  # Damn you, relative paths!
            thumb = 'http://www.swallowtailgardenseeds.com' + thumb
        elif 'http' not in thumb:
            thumb = 'http://www.swallowtailgardenseeds.com/' + thumb
        cv['thumbnail'] = thumb
    ems = cv_div.h3.find_all('em')
    botanical_name = None
    veg_data = None
    ems.pop(0)  # First em = common name, which isn't needed here.
    for em in ems:
        emt = em.text.strip()
        if 'days' in emt or '(OP)' in emt:
            veg_data = em.text.strip()
        else:
            botanical_name = em.text.strip()
    if botanical_name:
        if 'syn.' in botanical_name:
            # Remove synonym(s) if present because it could otherwise
            # cause weird duplicates in db. Hopefully the bn and its
            # synonym are in `self.common_name`, otherwise the synonym
            # will have to be manually added later.
            bn_parts = botanical_name.split(' syn. ')
            bn = bn_parts[0].replace(',', '').strip()
        else:
            bn = botanical_name
        cv['botanical name'] = bn
    if veg_data:
        if '(OP)' in veg_data:
            cv['open pollinated'] = True
        dtm = veg_data.replace('(OP)', '').replace('days', '').strip()
        if dtm:
            cv['days to maturity'] = dtm
    ps = cv_div.h3.find_next_siblings('p')
    if ps:
        desc = merge_p(ps)
        cv['description'] = desc.strip()

    button = cv_div.find(name='button')
    if not button:
        raise RuntimeError('Has no button: {0}'.format(cv_div))
    if 'out of stock' in button.text.lower():
        cv['in stock'] = False
    else:
        cv['in stock'] = True

    cv['active'] = True  # If the CV isn't active, it will be set False later.

    pkt_tds = cv_div.find_all('td')
    pkt_str = pkt_tds[0].text
    cv['packet'] = str_to_packet(pkt_str)
    cv['packet']['sku'] = cv_div.small.text.strip()
    cv['packet'].move_to_end('sku', last=False)
    if len(pkt_tds) == 2:  # Should indicate presence of jumbo packet.
        cv['jumbo'] = str_to_packet(pkt_tds[1].text)
        cv['jumbo']['sku'] = cv_div.small.text + 'J'
    return cv


def str_to_packet(pkt_str):
    """Split a string of packet data into price, quantity, and units.

    Note:
        Packet strings are in the format:

        '<quantity> <units> - <price>'

        e.g.:

        '100 seeds - $1.99'

    Returns:
        dict: The price, quantity, and units of the packet.
    """
    parts = pkt_str.split(' ')
    words = []
    nums = []
    for part in parts:
        part = part.strip()
        if part.replace('-', '').replace('.', '').isalpha():
            words.append(part)
        elif any(c.isdigit() for c in part):
            nums.append(part)
    try:
        price = next(n for n in nums if '$' in n)
    except StopIteration:
        raise RuntimeError('Could not find a price in: {0}'.format(pkt_str))
    nums.remove(price)
    price = ''.join(c for c in price if c.isdigit() or c == '.')
    qty = ' '.join(nums).replace(',', '')  # Get rid of , in 1,000 etc.
    units = ' '.join(words).lower()
    pkt = OrderedDict()
    pkt['price'] = price
    pkt['quantity'] = qty
    pkt['units'] = units
    return pkt

#    if '-' in pkt_str:
#        parts = pkt_str.strip().split('-')
#    else:
#        bits = pkt_str.strip().split(' ')
#        pr = bits.pop()
#        parts = [' '.join(bits), pr]
#    qty_and_units = parts[0].strip()
#    raw_price = parts[1].strip()
#    price = raw_price.replace('$', '')
#    qau_parts = qty_and_units.split(' ')
#    qty_parts = []
#    units_parts = []
#    for part in qau_parts:
#        # Replace '-' to handle hyphenated units like 'multi-pelleted seeds'
#        if part.replace('-', '').isalpha():
#            units_parts.append(part)
#        else:
#            qty_parts.append(part)
#    qty = ' '.join(qty_parts).replace(',', '')
#    units = ' '.join(units_parts).lower()
#    pkt = OrderedDict()
#    pkt['price'] = price
#    pkt['quantity'] = qty
#    pkt['units'] = units
#    return pkt


def get_sections(parent):
    """Get all sections in top level of parent."""
    sections = parent.find_all(name='section', recursive=False)
    return sections


def generate_cultivar_dicts(parent):
    """Yield dicts of all cultivars that are in the top level of parent."""
    cv_divs = parent.find_all(
        name='div',
        class_=lambda x: x and x.lower() == 'cultivar',
        recursive=False
    )
    for cv_div in cv_divs:
        yield(cultivar_div_to_dict(cv_div))


def generate_inactive_cultivar_dicts(parent):
    """Yield dicts of commented out cultivars to be added as inactive."""
    cv_divs_raw = parent.find_all(
        text=(lambda x: x
              and isinstance(x, Comment)
              and 'class="cultivar"' in x.lower()),
        recursive=False
    )
    cv_divs = [BeautifulSoup(d, 'html.parser').div for d in cv_divs_raw]
    for cv_div in cv_divs:
        cv_dict = cultivar_div_to_dict(cv_div)
        cv_dict['active'] = False
        yield(cv_dict)


def consolidate_sections(d):
    """Find duplicate sections near root of section tree and move to branches.

    Sometimes sections are duplicated, either by accident or for... reasons.
    As such, we need to account for that and fix it here.

    Args:
        d: The dict to check the sections in.
    """
    sections = dict()
    for s in list(d['sections']):
        sn = s['section name'].lower()
        if 'no section' in sn or 'no series' in sn:
            if 'cultivars' not in d:
                d['cultivars'] = []
            d['cultivars'] += s['cultivars']
            d['sections'].remove(s)
        else:
            sections[s['section name']] = s
            if 'sections' in s:
                for ss in list(s['sections']):
                    if ss['section name'] in sections:
                        sec = sections[ss['section name']]
                        ss['cultivars'] += sec['cultivars']
                        d['sections'].remove(sec)


class NewPage(object):
    """A crawled page to extract data from."""
    def __init__(self, url=None, filename=None, parser=None):
        self.url = url
        if not parser:
            parser = 'html.parser'
        if filename:
            with open(filename, 'r') as ifile:
                text = ifile.read()
        else:
            text = requests.get(url).text
        text = clean(text)
        self.soup = BeautifulSoup(text, parser)

    @property
    def main_div(self):
        """Return the div the main content of the page is in.

        Returns:
            main: The main section of the page.

        Raises:
            RuntimeError: If no main section can be found.
        """
        main = self.soup.find(name='div', id='main')
        if not main:
            main = self.soup.find(
                name='div', class_=lambda x: x and x.lower() == 'main'
            )
        if not main:
            main = self.soup.find(
                name='div', id=lambda x: x and x.lower() == 'maincontent'
            )
        if not main:
            main = self.soup.main
        if not main:
            raise RuntimeError('Could not find a main section in the page!')
        return main

    @property
    def common_name(self):
        MULTIPLES = ('bean',
                     'corn',
                     'lettuce',
                     'pepper',
                     'petunia',
                     'squash',
                     'tomato')

        cn = OrderedDict()
        header_div = self.soup.find(name='header')
        if not header_div:
            header_div = self.soup.find(
                name='div', class_=lambda x: x and x.lower() == 'header'
            )

        name = get_h_title(header_div.h1).strip().lower().replace('seeds', '')
        for m in MULTIPLES:
            if m in name and name != m:
                name = m + ', ' + name.replace(m, '').strip()
        cn['common name'] = dbify(name)

        if '/annuals/' in self.url:
            cn['index'] = 'Annual Flower'
        elif '/perennials/' in self.url:
            cn['index'] = 'Perennial Flower'
        elif '/vines/' in self.url:
            cn['index'] = 'Flowering Vine'
        elif '/veggies/' in self.url:
            cn['index'] = 'Vegetable'
        elif '/herbs/' in self.url:
            cn['index'] = 'Herb'

        if header_div.h2:
            cn['synonyms'] = header_div.h2.text.strip()

        if header_div.h3:
            bns_string = header_div.h3.text.strip()
            # TODO: Parse and clean botanical names before assignment.
            cn['botanical names'] = list(generate_botanical_names(bns_string))

        ps = header_div.find_all('p', recursive=False)
        if ps:
            cn['description'] = merge_p(ps)
        else:
            intro_div = self.main_div.find(name='div', class_='intro')
            if intro_div:
                ps = intro_div.find_all('p', recursive=False)
                cn['description'] = merge_p(ps)

        growing = self.main_div.find(
            name='div',
            class_=lambda x: x and x.lower() == 'growing'
        )
        if growing:
            cn['instructions'] = merge_p(growing.find_all('p'))

        return cn

    @property
    def sections(self):
        sd = OrderedDict()
        sd['sections'] = []
        for section in get_sections(self.main_div):
            sd['sections'].append(self.section_dict(section))

        return sd

    @property
    def tree(self):
        """Return the full tree of dicts containing CN page data."""
        tree = self.common_name

        tree['sections'] = list()
        for section in get_sections(self.main_div):
            tree['sections'].append(self.section_dict(section))

        cultivar_dicts = list(generate_cultivar_dicts(self.main_div))
        cultivar_dicts += list(generate_inactive_cultivar_dicts(self.main_div))
        if cultivar_dicts:
            tree['cultivars'] = cultivar_dicts

        consolidate_sections(tree)

        return tree

    @property
    def json(self):
        """str: JSONified version of `tree`."""
        return json.dumps(self.tree, indent=4)

    def section_dict(self, section):
        """Get a dict containing section and subsection data."""
        sd = OrderedDict()
        if section.h2:
            sec_name = get_h_title(section.h2)
        else:
            sec_class = section['class'][0]
            sec_name = sec_class.replace('-', ' ').lower()
        cn = self.common_name['common name'].lower()
        cn_seeds = cn + ' seeds'
        if cn_seeds in sec_name:
            sec_name = sec_name.replace(cn_seeds, '')
        else:
            sec_name = sec_name.replace('seeds', '')
        sd['section name'] = dbify(sec_name)

        desc_div = section.div
        if 'cultivar' not in (c.lower() for c in desc_div['class']):
            desc = merge_p(desc_div.find_all('p'))
            if desc:
                sd['description'] = desc

        cultivar_dicts = list(generate_cultivar_dicts(section))
        cultivar_dicts += list(generate_inactive_cultivar_dicts(section))
        if cultivar_dicts:
            sd['cultivars'] = cultivar_dicts

        subsections = get_sections(section)
        if subsections:
            sd['sections'] = []
            for subsec in subsections:
                sd['sections'].append(self.section_dict(subsec))

        return sd

    def save_json(self, filename):
        """Save JSON string to a file."""
        with open(filename, 'w') as outf:
            outf.write(self.json)


class Page(object):
    """Class for page to draw data from.

    Args:
        url: The URL to get page data from.
        parser: The HTML parser to use with `BeautifulSoup`.

    Attributes:
        url: The URL the page was grabbed from.
        soup: A `BeautifulSoup` object generated from text HTML.
    """
    def __init__(self, url, parser=None):
        self.url = url
        text = requests.get(url).text
        if not parser:
            parser = 'html.parser'
        text = clean(text)
        self.soup = BeautifulSoup(text, parser)

    @property
    def common_name(self):
        """OrderedDict: `CommonName` data from page header."""
        if self.soup.header:
            header = self.soup.header
        else:
            header = self.soup
        cn = OrderedDict()
        cn_name = header.h1.text.lower().replace('seeds', '')
        MULTIPLES = ('bean', 'corn', 'lettuce', 'pepper', 'squash', 'tomato')
        for m in MULTIPLES:
            if m in cn_name:
                cn_name = m + ', ' + cn_name.replace(m, '').strip()
        cn['common name'] = dbify(cn_name)
        if '/annuals/' in self.url:
            cn['index'] = 'Annual Flower'
        elif '/perennials/' in self.url:
            cn['index'] = 'Perennial Flower'
        elif '/vines/' in self.url:
            cn['index'] = 'Flowering Vine'
        elif '/veggies/' in self.url:
            cn['index'] = 'Vegetable'
        elif '/herbs/' in self.url:
            cn['index'] = 'Herb'
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
                    bn = expand_botanical_name(bn, abbreviations)
                    if bn[:4] == 'syn.':
                        botanical_names[-1] = botanical_names[-1] + ' ' + bn
                    else:
                        if ' syn. ' in bn:
                            # Un-abbreviate synonyms so we don't have to later.
                            for key in abbreviations:
                                bn = bn.replace(key, abbreviations[key])
                        # Do not append if it was a synonym.
                        botanical_names.append(bn)
            cn['botanical names'] = botanical_names
        desc_divs = self.soup.find_all(class_='intro')
        if desc_divs:
            desc_div = desc_divs[0]
            ps = desc_div.find_all('p')
        else:
            ps = header.h1.find_next_siblings('p')
        if ps:
            cn['description'] = merge_p(ps)

        inst_divs = self.soup.find_all(class_='growing')
        if inst_divs:
            inst_div = inst_divs[0]
            cn['instructions'] = merge_p(inst_div.find_all('p'))
        return cn

    @property
    def sections(self):
        """Get a list of sections and their data in `OrderedDict`s.

        This includes the cultivars belonging to the section.

        Returns:
            list: List of `OrderedDict` containing `Section` data.
        """
        def cultivar_divs(sec):
            """Generate divs containing `Cultivar` data for `sec`.

            Args:
                sec: The section div to find related cultivars for.

            Yields:
                div: A div containing cultivar data.
            """
            for div in sec.find_next_siblings(name='div'):
                if 'class' in div.attrs:
                    if 'cultivar' in [c.lower() for c in div['class']]:
                        yield div
                    else:
                        break

        secs = self.soup.find_all(
            name='div', class_=lambda x: x and ('categor' in x.lower() or
                                                'series' in x.lower())
        )
        sections = []
        for sec in secs:
            secd = OrderedDict()
            secd['section name'] = dbify(sec.text.strip().split('\n')[0])
            ps = sec.find_all('p')
            if ps:
                secd['description'] = merge_p(ps)
            cvds = cultivar_divs(sec)
            if cvds:
                secd['cultivars'] = [cultivar_div_to_dict(cvd) for cvd in cvds]
            sections.append(secd)
        return sections

    @property
    def individual_cultivars(self):
        """Return a list of `OrderedDict` of `Cultivar` not in a `Section`."""
        if self.sections:
            for sec in self.sections:
                if 'individual' in sec['section name'].lower():
                    return sec['cultivars']
            return []
        else:
            cv_divs = self.soup.find_all(name='div', class_='cultivar')
            return [cultivar_div_to_dict(cvd) for cvd in cv_divs]

    @property
    def tree(self):
        """OrderedDict: A tree of all data with `common_name` as the root."""
        cn = self.common_name
        secs = self.sections
        for sec in list(secs):
            if 'individual' in sec['section name'].lower():
                secs.remove(sec)
        cn['sections'] = secs
        cn['cultivars'] = self.individual_cultivars
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
    def __init__(self, tree, index=None):
        self.tree = tree
        if index:
            self.index = index
        else:
            self.index = Index.get_or_create(tree['index'])

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
            if 'new until' in cvd:
                cv_nu = cvd['new until']
            else:
                cv_nu = None
            if 'thumbnail' in cvd:
                cv_thumb = cvd['thumbnail']
            else:
                cv_thumb = None
            if 'botanical name' in cvd:
                cv_bn = cvd['botanical name']
            else:
                cv_bn = None
            if 'open pollinated' in cvd:
                cv_op = cvd['open pollinated']
            else:
                cv_op = None
            if 'days to maturity' in cvd:
                cv_dtm = cvd['days to maturity']
            else:
                cv_dtm = None
            if 'description' in cvd:
                cv_desc = cvd['description']
            else:
                cv_desc = None
            if 'in stock' in cvd:
                cv_in_stock = cvd['in stock']
            else:
                cv_in_stock = None
            if 'active' in cvd:
                cv_active = cvd['active']
            else:
                cv_active = None
            cv_pkts = []
            if 'packet' in cvd:
                cv_pkts.append(cvd['packet'])
            if 'jumbo' in cvd:
                cv_pkts.append(cvd['jumbo'])

            cv = Cultivar.get_or_create(name=cv_name,
                                        common_name=cn.name,
                                        index=cn.index.name,
                                        stream=stream)
            if cv_nu:
                cv.new_until = datetime.datetime.strptime(cv_nu,
                                                          '%m/%d/%Y').date()
                cv.featured = True  #TODO: Handle featured better.

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
            if cv_op is not None or cv_dtm:
                if not cv.vegetable_data:
                    cv.vegetable_data = VegetableData()
                if cv_op:
                    cv.vegetable_data.open_pollinated = True
                    print('\'{0}\' is open pollinated.'
                          .format(cv.fullname), file=stream)
                else:
                    cv.vegetable_data.open_pollinated = False
                    print('\'{0}\' is not open pollinated.'
                          .format(cv.fullname), file=stream)
                if cv_dtm:
                    cv.vegetable_data.days_to_maturity = cv_dtm
                    print('\'{0}\' is expected to mature in {1} days.'
                          .format(cv.fullname, cv_dtm), file=stream)
            if cv_desc and cv.description != cv_desc:
                cv.description = cv_desc
                print('Description for \'{0}\' set to: {1}'
                      .format(cv.fullname, cv.description), file=stream)
            if cv_in_stock is not None:
                cv.in_stock = cv_in_stock
                print('\'{0}\' is {1}.'
                      .format(cv.fullname,
                              'in stock' if cv.in_stock else 'out of stock'),
                      file=stream)
            if cv_active is not None:
                cv.active = cv_active
                print('\'{0}\' is {1}.'
                      .format(cv.fullname,
                              'active' if cv.active else 'inactive'),
                      file=stream)
            if cv_pkts:
                for cv_pkt in cv_pkts:
                    sku = cv_pkt['sku']
                    price = cv_pkt['price']
                    qty = cv_pkt['quantity']
                    units = cv_pkt['units']
                    pkt = Packet.query.filter(Packet.sku == sku).one_or_none()
                    if pkt:
                        if pkt.cultivar and pkt.cultivar is not cv:
                            print('WARNING: The packet for \'{0}\' with the '
                                  'SKU \'{1}\' was not added because another '
                                  'packet already exists with the same SKU!'
                                  .format(cv.fullname, pkt.sku), file=stream)
                            pkt = None
                        else:
                            if not pkt.cultivar:
                                pkt.cultivar = cv
                    else:
                        pkt = Packet(sku=sku)
                    if pkt:
                        pkt.price = price
                        if not pkt.quantity:
                            pkt.quantity = Quantity.query\
                                .filter(Quantity.value == qty,
                                        Quantity.units == units)\
                                .one_or_none()
                            if not pkt.quantity:
                                pkt.quantity = Quantity()
                        pkt.quantity.value = qty
                        pkt.quantity.units = units
                        if pkt not in cv.packets:
                            cv.packets.append(pkt)
                        print('Packet \'{0}\' added to \'{1}\'.'
                              .format(pkt.info, cv.fullname), file=stream)
            cv.visible = False
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
        # TODO: Handle whether or not cn is visible.

        if 'botanical names' in self.tree:
            bn_names = self.tree['botanical names']
            for bn_name in bn_names:
                bn_and_syn = None
                if 'syn.' in bn_name:
                    bn_and_syn = bn_name.split(' syn. ')
                    bn_name = bn_and_syn.pop(0)
                bn = BotanicalName.get_or_create(bn_name,
                                                 stream=stream,
                                                 fix_bad=True)
                if bn_and_syn:  # Empty if no synonyms.
                    print(bn_and_syn)
                    # TODO: Make this expand abbreviated genus in synonym.
                    bn.synonyms_string = ', '.join(bn_and_syn)
                if bn not in cn.botanical_names:
                    cn.botanical_names.append(bn)
                    print('Botanical name \'{0}\' added to \'{1}\'.'
                          .format(bn.name, cn.name), file=stream)
        if 'sections' in self.tree:
            for sec in self.generate_sections(cn,
                                              self.tree['sections'],
                                              stream=stream):
                cn.sections.append(sec)
                print('Section \'{0}\' and its subsections added to \'{1}\'.'
                      .format(sec.name, cn.name), file=stream)
        if 'cultivars' in self.tree:
            for cv in self._generate_cultivars(cn=cn,
                                               cv_dicts=self.tree['cultivars'],
                                               stream=stream):
                print('Cultivar \'{0}\' added to CommonName \'{1}\'.'
                      .format(cv.fullname, cn.name), file=stream)
        db.session.commit()

    def generate_sections(self, cn, section_dicts, stream=sys.stdout):
        """Generate sections from section_dicts."""
        for secd in section_dicts:
            sec_name = secd['section name']
            if 'description' in secd:
                sec_desc = secd['description']
            else:
                sec_desc = None
            sec = Section.get_or_create(name=sec_name,
                                        common_name=cn.name,
                                        index=self.index.name)
            if sec_desc and sec.description != sec_desc:
                sec.description = sec_desc
                print('Description for \'{0}\' set to: {1}'
                      .format(sec.name, sec.description), file=stream)

            if 'cultivars' in secd:
                sec_cvds = secd['cultivars']
                for cv in self._generate_cultivars(cn=cn,
                                                   cv_dicts=sec_cvds,
                                                   stream=stream):
                    if cv not in sec.cultivars:
                        sec.cultivars.append(cv)
                        print('Cultivar \'{0}\' added to Section \'{1}\'.'
                              .format(cv.fullname, sec.fullname),
                              file=stream)

            if 'sections' in secd:
                sec.children = list(self.generate_sections(cn,
                                                           secd['sections'],
                                                           stream=stream))

            yield sec


class Thumbnail(object):
    """Class for handling thumbnail images."""
    def __init__(self, url):
        self.url = url
        self.filename = secure_filename(os.path.split(self.url)[-1])
        self.directory = os.path.join(current_app.config.get('IMAGES_FOLDER'),
                                      'plants')

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
            img.raise_for_status()

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
            if row_exists(Image.filename, self.filename):
                raise RuntimeError('Attempt to rename thumbnail failed, as an '
                                   'image named \'{0}\' already exists!'
                                   .format(self.filename))
        self.download()
        return Image(filename=self.filename)
