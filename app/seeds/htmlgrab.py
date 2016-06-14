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
import re
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
    VegetableData
)


def save_batch(lines, index, directory=None, pages_dir=None):
    """Save a batch of pages to JSON.

    Args:
        lines: A multi-line string containing URLs and optionally corrected
            pages.
        directory: The directory to save JSON files to.
    """
    if not directory:
        directory = os.path.join('/tmp', index)
    if not os.path.exists(directory) and directory[:4] == '/tmp':
        os.mkdir(directory)
    if not pages_dir:
        pages_dir = os.path.join(os.getcwd(), '909', index)
    for line in lines:
        if line[0] == '#':
            print('Line is commented out: {0}'.format(line))
            continue

        if '#' in line:
            comment = line[line.index('#'):]
            line = line[:line.index('#')].strip()
        else:
            comment = None
        parts = line.split(' ')
        url = parts[0]
        if len(parts) > 2:
            raise ValueError('The line {0} has too many spaces!'.format(line))
        elif len(parts) == 2:
            page = os.path.join(pages_dir, parts[1])
        else:
            page = None

        if page:
            p = Page(url=url, filename=page)
            print('USING PAGE: {0}'.format(page), end='\t')
        else:
            p = Page(url=url)
        filename = os.path.splitext(os.path.split(url)[1])[0]
        jfile = os.path.join(directory, filename + '.json')
        p.save_json(jfile)
        print('Saving data from {0} to {1}'.format(url, jfile),
              end='\t' if comment else '\n')
        if comment:
            print('Comment: {0}'.format(comment))
    print('All pages in this batch were saved.')


def clean(text, unwanted=None):
    """Remove unwanted characters/substrings from a block of text.

    Returns:
        str: Cleaned up version of `text`.
    """
    REPLACEMENTS = {
        # Fractions
        '&frac14;': '1/4',
        '&frac12;': '1/2',
        '&frac34;': '3/4',
        '&frac18;': '1/8',
        '&#8539;': '1/8',
        '&#8531;': '1/3',
        '\u00bc': '1/4',
        '\u00bd': '1/2',
        '\u00be': '3/4',
        '\u215b': '1/8',
        '\u2153': '1/3',
        # Unicode weirdness
        '\xa0': ' ',
        '\u2019': '\'',
        # Common errors
        '&#176F': '&#176;F'
    }
    for r in REPLACEMENTS:
        text = text.replace(r, REPLACEMENTS[r])
    # Replace tabs preceded by non-space with spaces before stripping out tabs.
    text = re.sub(r'([^\s])\t', r'\1 ', text)
    if not unwanted:
        unwanted = ['\r', '\t', '&shy;', '<br>', '<br \>', '</img>']
    for u in unwanted:
        text = text.replace(u, '')
    # Deal with commented out product info.
    text = re.sub('--><!--.*--><!--', '', text)
    # Deal with multiple classes in sequence.
    text = re.sub(r'(class="[a-zA-Z0-9_-]*") class="[a-zA-Z0-9_-]*"',
                  r'\1',
                  text)
    # Convert HTML5 void elements to HTML4 because html.parser is dumb.
    # For the sake of efficiency, not all void elements are checked, as most
    # of them are either unused, or not used in a way that will cause problems
    # if html.parser tries to close them.
    VOID_ELEMENTS = [
        r'img',
        r'input'
    ]
    for v in VOID_ELEMENTS:
        text = re.sub(r'(<' + v + '.*?)>', r'\1 />', text)
    return text.strip()


def remove_comments(tag):
    """Remove all comments from within the given tag."""
    for c in tag(text=lambda x: isinstance(x, Comment)):
        c.extract()


def merge_p(p_tags):
    """Merge a list of paragraphs into a single block of text."""
    p_tags = [p for p in p_tags if p and p.text]
    for tag in p_tags:
        remove_comments(tag)
    return '\n'.join(str(p) for p in p_tags if 'go-to-next' not in str(p))


def get_h_title(tag):
    """Attempt to parse the title in an h1, h2, etc. block."""
    # Remove comments from within h tags, as they screw up tag.contents.
    for t in tag(text=lambda x: isinstance(x, Comment)):
        t.extract()
    try:
        title = next(c for c in tag.contents if c and hasattr(c, 'isspace')
                     and not c.isspace())
    except TypeError:
            b = tag.find('b')
            title = b.text
    except StopIteration:
        raise RuntimeError('Could not isolate the title in: {0}'.format(tag))
    except Exception as e:
        raise RuntimeError('An exception \'{0}\' was raised when trying to '
                           'get the title out of: {1}'.format(e, tag))
    return title.strip().lower()


def generate_botanical_names(bns_string):
    """Clean up a string listing multiple botanical names as a header."""
    abbr = dict()
    bns_string = re.sub(r'\.([a-zA-z])', r'. \1', bns_string)
    bns = bns_string.replace(', syn.', ' syn.').split(', ')
    bns = [b.strip() for b in bns]
    bns = sorted(bns, key=lambda x: len(x.split()[0]), reverse=True)
    for bn in bns:
        try:
            yield expand_botanical_name(bn, abbr)
        except IndexError as e:
            raise RuntimeError(
                'Invalid bn {0} in {1}'.format(bn, bns_string)
            ).with_traceback(e.__traceback__)
        except KeyError as e:
            raise RuntimeError(
                'Index error {0} in botanical names {1}'.format(e, bns_string),
            ).with_traceback(e.__traceback__)


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
    parts = [p for p in parts if p and not p.isspace()]
    first = parts[0]
    abbr = first[0] + '.'
    if len(first) > 2 and abbr not in abbreviations:
            abbreviations[abbr] = first
    bn = bn.replace(abbr, abbreviations[abbr])
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
    cv['cultivar name'] = dbify(' '.join(cv_name.split()))  # Fix whitespace.
    try:
        cv['anchor'] = cv_div.h3['id']
    except KeyError:
        pass
    if cv_div.h3.em:
        cv['subtitle'] = dbify(cv_div.h3.em.text.strip())
    if 'new for 2016' in cv_div.text.lower():
        cv['new until'] = '12/31/2016'
    if cv_div.img:
        thumb = cv_div.img['src']
        if thumb[0] == '/':  # Damn you, relative paths!
            thumb = 'http://www.swallowtailgardenseeds.com' + thumb
        elif 'http' not in thumb:
            thumb = 'http://www.swallowtailgardenseeds.com/' + thumb
            thumb = thumb.replace('../', '')
        cv['thumbnail'] = thumb
    ems = cv_div.h3.find_all('em')
    botanical_name = None
    veg_data = None
    if ems:
        ems.pop(0)  # First em = common name, which isn't needed here.
        for em in ems:
            emt = em.text.strip()
            if 'days' in emt.lower() or '(OP)' in emt:
                veg_data = em.text.strip()
                parts = veg_data.split(',')
                for part in list(parts):
                    if 'days' not in part.lower() and '(OP)' not in part:
                        botanical_name = part.strip()
                        parts.remove(part)
                        veg_data = ' '.join(parts)
                veg_data = veg_data.replace(',', '')
                v = veg_data.replace('(OP)', '').replace('(Hyb.)', '').strip()
                if v and not v.isspace() and 'days' not in v.lower():
                    botanical_name = v
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
            if 'hyb' in veg_data.lower():
                cv['hybrid'] = True
            if 'days' in veg_data:
                dtm = veg_data.replace('(OP)', '').replace('(Hyb.)', '')
                if dtm:
                    cv['days to maturity'] = dtm.strip()
    ps = cv_div.h3.find_next_siblings('p')
    if ps:
        spans = ps[-1].find_next_siblings('span')
        if spans:
            ps = ps + spans
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
    try:
        pkt_str = pkt_tds[0].text
    except IndexError as e:
        raise RuntimeError('IndexError triggered making packet for {0}.'
                           .format(cv_div))
    cv['packet'] = str_to_packet(pkt_str)
    partno = cv_div.find('input', {'name': 'PartNo'})
    if partno:

        cv['packet']['sku'] = partno['value']
    else:
        small = cv_div.small
        if small:
            cv['packet']['sku'] = small.text.strip()
        else:
            raise RuntimeError(
                'Could not find sku in: {0}'.format(cv_div)
            ).with_traceback(e.__traceback__)
    cv['packet'].move_to_end('sku', last=False)
    if len(pkt_tds) == 2:  # Should indicate presence of jumbo packet.
        cv['jumbo'] = str_to_packet(pkt_tds[1].text)
        cv['jumbo']['sku'] = cv_div.small.text + 'J'
    return cv


def generate_cultivar_dicts(parent):
    """Yield dicts of all cultivars that are in the top level of parent."""
    cv_divs = parent.find_all(
        name='div',
        class_=lambda x: x and x.lower() == 'cultivar',
        recursive=False
    )

    def fix_holdums(holdums):
        """Yield parent divs of holdums with the holdum divs unwrapped."""
        for holdum in holdums:
            p = holdum.parent
            while p.name != 'div':
                if p is parent:
                    raise RuntimeError(
                        'Could not find a parent cultivar div for holdum: {0}'
                        .format(holdum)
                    )
                else:
                    p = p.parent
            holdum.unwrap()
            yield p

    holdums = parent.find_all(name='div',
                              class_=lambda x: x and x.lower() == 'holdum')
    if holdums:
        for fixed in fix_holdums(holdums):
            cv_divs.append(fixed)
    for cv_div in cv_divs:
        yield cultivar_div_to_dict(cv_div)


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
    parts = pkt_str.replace(':', '').split(' ')
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
        p = nums[-1]
        if '.' in p and p.replace('.', '').isdigit():
            price = p.strip()
        else:
            raise RuntimeError('Could not find a price in: {0}'
                               .format(pkt_str))
    nums.remove(price)
    price = ''.join(c for c in price if c.isdigit() or c == '.')
    if not price:
        raise ValueError('Could not parse price from: {0}'
                         .format(pkt_str))
    qty = ' '.join(nums).replace(',', '')  # Get rid of , in 1,000 etc.
    if not qty:
        raise ValueError('Could not parse quantity from: {0}'
                         .format(pkt_str))
    units = ' '.join(words).lower().strip('-')
    if not units:
        raise ValueError('Could not parse unit of measure from: {0}'
                         .format(pkt_str))
    pkt = OrderedDict()
    pkt['price'] = price
    pkt['quantity'] = qty
    pkt['units'] = units
    return pkt


def get_sections(parent):
    """Get all sections in top level of parent."""
    sections = parent.find_all(name='section', recursive=False)
    return sections


def consolidate_sections(d):
    """Find duplicate sections near root of section tree and move to branches.

    Sometimes sections are duplicated, either by accident or for... reasons.
    As such, we need to account for that and fix it here.

    Args:
        d: The dict to check the sections in.
    """
    sections = dict()
    for s in list(d['sections']):
        sn = s['section name']
        if 'individual' in sn.lower() and 'variet' in sn.lower():
            if 'cultivars' not in d:
                d['cultivars'] = list()
            d['cultivars'] += s['cultivars']
            d['sections'].remove(s)
        elif sn in sections:
            sec = sections[sn]
            if 'cultivars' not in s:
                s['cultivars'] = list()
            s['cultivars'] += sec['cultivars']
            d['sections'].remove(sec)
        elif 'no section' in sn.lower() or 'no series' in sn.lower():
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
                        try:
                            ss['cultivars'] += sec['cultivars']
                        except KeyError as k:
                            raise RuntimeError(
                                'Key {0} missing from {1}'.format(k, sec)
                            ).with_traceback(sys.exc_info()[2])
                        d['sections'].remove(sec)


def clean_cultivar_dicts(cultivar_dicts, cn):
    """Remove unwanted subtitles from cultivar dicts."""
    for cd in cultivar_dicts:
        if 'subtitle' in cd:
            if not cd['subtitle']:
                cleaned = None
            else:
                try:
                    st = cd['subtitle'].lower()
                except AttributeError as e:
                    raise RuntimeError(
                        'AttributeError {0} raised when trying to set '
                        'subtitle for: {1}'.format(e, cd)
                    ).with_traceback(e.__traceback__)
                cleaned = st.replace(cn.lower(), '').replace('seeds', '')
            if not cleaned or cleaned.isspace():
                cd.pop('subtitle')


def split_botanical_name_synonyms(bn):
    """Split a botanical name string into botanical name and synonyms."""
    if 'syn.' in bn:
        parts = bn.split(' syn. ')
        return (parts[0], parts[1:])
    else:
        return (bn, [])


class Page(object):
    """A crawled page to extract data from."""
    def __init__(self, url=None, filename=None, parser=None):
        self.url = url
        if not parser:
            parser = 'html.parser'
        self.parser = parser
        if filename:
            with open(filename, 'r') as ifile:
                text = ifile.read()
        else:
            r = requests.get(url)
            r.encoding = 'utf-8'
            text = r.text
        text = clean(text)
        self.soup = BeautifulSoup(text, self.parser)

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
        INDEXES = ('annual', 'perennial')

        cn = dict()
        header_div = self.soup.find(name='header')
        if not header_div:
            header_div = self.soup.find(
                name='div', class_=lambda x: x and x.lower() == 'header'
            )
        if not header_div:
            h1 = self.main_div.find('h1')
            html = str(h1)
            for t in h1.next_siblings:
                if isinstance(t, Tag) and t.name == 'div':
                    break
                else:
                    html += str(t)
            header_div = BeautifulSoup(html, self.parser)

        name = get_h_title(header_div.h1).strip().lower().replace('seeds', '')
        for i in INDEXES:
            if i in name:
                name = name.replace(i, '').strip()
        cn['common name'] = dbify(name)

        if '/annuals/' in self.url:
            ipage = 'http://www.swallowtailgardenseeds.com/annualsA-Z.html'
            cn['index'] = 'Annual Flower'
        elif '/perennials/' in self.url:
            ipage = 'http://www.swallowtailgardenseeds.com/perennialsA-Z.html'
            cn['index'] = 'Perennial Flower'
        elif '/vines/' in self.url:
            ipage = 'http://www.swallowtailgardenseeds.com/vinesaz.html'
            cn['index'] = 'Flowering Vine'
        elif '/veggies/' in self.url or '/vegetables/' in self.url:
            ipage = 'http://www.swallowtailgardenseeds.com/vegetablesaz.html'
            cn['index'] = 'Vegetable'
        elif '/herbs/' in self.url:
            ipage = 'http://www.swallowtailgardenseeds.com/herbsaz.html'
            cn['index'] = 'Herb'

        cn['url'] = self.url

        # Get thumbnail from ipage.
        r = requests.get(ipage)
        soup = BeautifulSoup(r.text, self.parser)
        a = soup.find('a', href=self.url)
        thumb = a.img
        if thumb:
            cn['thumbnail'] = thumb['src']

        if header_div.h2:
            cn['synonyms'] = header_div.h2.text.strip()

        if (header_div.h3
                and header_div.h3.text
                and not header_div.h3.text.isspace()):
            bns_string = header_div.h3.text.strip()
            # TODO: Parse and clean botanical names before assignment.
            cn['botanical names'] = list(generate_botanical_names(bns_string))
        intro = header_div.find_next_sibling(
            name='div', class_=lambda x: x and 'intro' in x.lower()
        )
        if 'heirloom.html' in self.url:  # Page has intro in a cultivar div.
            # Extract div to prevent it from being parsed as a cultivar.
            intro = self.main_div.find('div', class_='Cultivar').extract()
        if intro:
            ps = intro.find_all('p', recursive=False)
        else:
            ps = None
        if not ps:
            ps = header_div.find_all('p', recursive=False)
        if not ps:
            ps = header_div.find_next_siblings('p')
        else:
            intro_div = self.main_div.find(name='div', class_='intro')
            if intro_div:
                ps = intro_div.find_all('p', recursive=False)
        if ps:
            ps = [p for p in ps if 'how-to-plant' not in str(p)]
        if ps:
            spans = ps[-1].find_next_siblings('span')
            if spans:
                ps = ps + spans
        if ps:
            cn['description'] = merge_p(ps)

        growing = self.main_div.find_all(
            name='div',
            class_=lambda x: x and x.lower() == 'growing'
        )
        harvest = None
        if growing:
            if len(growing) == 2:
                harvest = growing[0]
                planting = growing[1]
            else:
                planting = growing[0]
            cn['instructions'] = merge_p(planting.find_all('p'))
        if not harvest:
            harvest = self.main_div.find(
                name='div', class_=lambda x: x and 'harvest' in x.lower()
            )
        if harvest:
            cn['harvesting'] = ''.join(str(c) for c in harvest.contents)

        grows_with = self.main_div.find(
            'div', class_=lambda x: x and 'relatedlinks' in x.lower()
        )
        if grows_with:
            cn['grows with'] = ''.join(str(c) for c in grows_with.contents)

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

        # Milk Thistle has a weird cultivar div that's classed 'Section'
        if 'thistle_milk.html' in self.url:
            scv = self.main_div.find('div', class_='Section')
            # Add 'cultivar' to classes so generate_cultivar_dicts finds it.
            scv.attrs['class'].append('cultivar')

        cultivar_dicts = list(generate_cultivar_dicts(self.main_div))
        cultivar_dicts += list(generate_inactive_cultivar_dicts(self.main_div))
        clean_cultivar_dicts(cultivar_dicts,
                             self.common_name['common name'].lower())
        if cultivar_dicts:
            tree['cultivars'] = cultivar_dicts

        ordered_keys = [
            'common name',
            'index',
            'url',
            'thumbnail',
            'synonyms',
            'botanical names',
            'description',
            'sections',
            'cultivars',
            'grows with',
            'harvesting',
            'instructions'
        ]
        for key in tree.keys():
            if key not in ordered_keys:
                raise RuntimeError(
                    'The key \'{0}\' is present in tree, but not in otree!'
                    .format(key)
                )

        otree = OrderedDict()
        for key in ordered_keys:
            if key in tree:
                otree[key] = tree[key]

        return otree

    def section_dict(self, section):
        """Get a dict containing section and subsection data."""
        sd = OrderedDict()
        h2 = section.find(name='h2', recursive=False)
        cn = self.common_name['common name'].lower()
        cn_seeds = cn + ' seeds'
        sdiv = section.find(
            name='div',
            class_=lambda x: x and 'cultivar' not in x.lower(),
            recursive=False
        )
        if not h2:
            if sdiv:
                h2 = sdiv.find(name='h2', recursive=False)
        if h2:
            sec_name = get_h_title(h2)
        else:
            try:
                sec_class = section['class'][0]
            except KeyError as e:
                if 'id' in section.attrs:
                    sec_class = section['id']
                else:
                    raise RuntimeError(
                        'KeyError {0} raised attempting to find class in '
                        'section: {1}'.format(e, section)
                    ).with_traceback(e.__traceback__)
            sec_name = sec_class.replace('-', ' ').lower()
            if cn_seeds in sec_name:
                sec_name = sec_name.replace(cn_seeds, '')
            else:
                sec_name = sec_name.replace('seeds', '')
        sd['section name'] = dbify(sec_name)

        if sdiv:
            bns = None
            if sdiv.h2:
                ems = sdiv.h2.find_all(name='em', recursive=False)
            else:
                ems = None
            if not ems:
                ems = sdiv.find_all(name='em', recursive=False)
            if ems:
                for em in ems:
                    text = em.text.strip().lower()
                    if 'seeds' in text:
                        if text != cn_seeds and text != 'seeds':
                            sd['subtitle'] = dbify(text)
                    elif len(text.split(' ')) > 1:
                            bns = em.text.strip()
            h3bot = sdiv.find(name='h3',
                              class_=lambda x: x and 'bot' in x.lower(),
                              recursive=False)
            if h3bot:
                bns = h3bot.text.strip()
            if bns:
                sd['botanical names'] = list(generate_botanical_names(bns))
            desc = merge_p(sdiv.find_all('p'))
            desc = desc.replace('<p></p>', '')
            if desc and not desc.isspace():
                sd['description'] = desc

        cultivar_dicts = list(generate_cultivar_dicts(section))
        cultivar_dicts += list(generate_inactive_cultivar_dicts(section))
        if cultivar_dicts:
            # We don't need subtitles unless they differ from '<CN> Seeds'.
            clean_cultivar_dicts(cultivar_dicts, cn)
            sd['cultivars'] = cultivar_dicts

        subsections = get_sections(section)
        if subsections:
            sd['sections'] = []
            for subsec in subsections:
                sd['sections'].append(self.section_dict(subsec))

        return sd

    @property
    def json(self):
        """str: JSONified version of `tree`."""
        t = self.tree
        consolidate_sections(t)
        return json.dumps(t, indent=4)

    def save_json(self, filename):
        """Save JSON string to a file."""
        if filename[-5:] != '.json':
            filename += '.json'
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
            cv_st = cvd['subtitle'] if 'subtitle' in cvd else None
            cv_nu = cvd['new until'] if 'new until' in cvd else None
            cv_thumb = cvd['thumbnail'] if 'thumbnail' in cvd else None
            cv_bn = cvd['botanical name'] if 'botanical name' in cvd else None
            cv_op = cvd['open pollinated'] if 'open pollinated' in cvd else \
                None
            cv_hyb = cvd['hybrid'] if 'hybrid' in cvd else None
            cv_dtm = cvd['days to maturity'] if 'days to maturity' in cvd \
                else None
            cv_desc = cvd['description'] if 'description' in cvd else None
            cv_in_stock = cvd['in stock'] if 'in stock' in cvd else None
            cv_active = cvd['active'] if 'active' in cvd else None
            cv_pkts = []
            if 'packet' in cvd:
                cv_pkts.append(cvd['packet'])
            if 'jumbo' in cvd:
                cv_pkts.append(cvd['jumbo'])

            cv = Cultivar.get_or_create(name=cv_name,
                                        common_name=cn.name,
                                        index=cn.index.name,
                                        stream=stream)
            if cv_st:
                cv.subtitle = cv_st
                print('Subtitle for {0} set to: {1}'
                      .format(cv.fullname, cv.subtitle), file=stream)
            if cv_nu:
                cv.new_until = datetime.datetime.strptime(cv_nu,
                                                          '%m/%d/%Y').date()
                cv.featured = True  # TODO: Handle featured better.

            if cv_thumb:
                thumb = Thumbnail(cv_thumb)
                if not cv.thumbnail or thumb.filename != cv.thumbnail.filename:
                    try:
                        cv.thumbnail = thumb.save()
                        print('Thumbnail for \'{0}\' set to \'{1}\'.'
                              .format(cv.fullname, thumb.filename),
                              file=stream)
                    except requests.exceptions.HTTPError as e:
                        cv.thumbnail = None
                        print('Thumbnail for {0} was not saved because an '
                              'HTTP Error was raised when trying to download '
                              'it: {1}'.format(cv.fullname, e), file=stream)
            if cv_bn:
                bn = BotanicalName.get_or_create(name=cv_bn,
                                                 stream=stream,
                                                 fix_bad=True)
                if bn not in cn.botanical_names:
                    cn.botanical_names.append(bn)
                    print('Added BotanicalName \'{0}\' to \'{1}\'.'
                          .format(bn.name, cn.name), file=stream)
                cv.botanical_name = bn
            if cv_op or cv_hyb or cv_dtm:
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
                if cv_hyb:
                    cv.vegetable_data.hybrid = True
                    print('\'{0}\' is a marked as hybrid.'
                          .format(cv.fullname), file=stream)
                else:
                    cv.vegetable_data.hybrid = False
                    print('\'{0}\' is not marked as hybrid.'
                          .format(cv.fullname), file=stream)
                if cv_dtm:
                    cv.vegetable_data.days_to_maturity = cv_dtm
                    print('\'{0}\' is expected to mature in {1}.'
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
        cn_url = self.tree['url']
        if 'thumbnail' in self.tree:
            cn_thumb = self.tree['thumbnail']
        else:
            cn_thumb = None
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
        if cn_thumb:
            thumb = Thumbnail(cn_thumb)
            if not cn.thumbnail or thumb.filename != cn.thumbnail.filename:
                try:
                    cn.thumbnail = thumb.save()
                    print('Thumbnail for \'{0}\' set to \'{1}\'.'
                          .format(cn.name, thumb.filename),
                          file=stream)
                except requests.exceptions.HTTPError as e:
                    cn.thumbnail = None
                    print('Thumbnail for {0} was not saved because an '
                          'HTTP Error was raised when trying to download '
                          'it: {1}'.format(cn.name, e), file=stream)
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
                bn_and_syns = split_botanical_name_synonyms(bn_name)
                bn = BotanicalName.get_or_create(bn_and_syns[0],
                                                 stream=stream,
                                                 fix_bad=True)
                if bn_and_syns[1]:  # Empty if no synonyms.
                    bn.synonyms_string = ', '.join(bn_and_syns[1])
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
            if 'subtitle' in secd:
                sec_sub = secd['subtitle']
            else:
                sec_sub = None
            if 'botanical names' in secd:
                sec_bots = secd['botanical names']
            else:
                sec_bots = None
            if 'description' in secd:
                sec_desc = secd['description']
            else:
                sec_desc = None
            sec = Section.get_or_create(name=sec_name,
                                        common_name=cn.name,
                                        index=self.index.name,
                                        stream=stream)
            if sec_sub:
                sec.subtitle = sec_sub
                print('Subtitle for section \'{0}\' set to: {1}'
                      .format(sec.name, sec.subtitle), file=stream)
            if sec_bots:
                for bot in sec_bots:
                    bn_and_syns = split_botanical_name_synonyms(bot)
                    bn = BotanicalName.get_or_create(name=bn_and_syns[0],
                                                     fix_bad=True,
                                                     stream=stream)
                    if bn_and_syns[1]:
                        bn.synonyms_String = ', '.join(bn_and_syns[1])
                    if bn not in sec.botanical_names:
                        sec.botanical_names.append(bn)
                        print('Added botanical name \'{0}\' to section: '
                              '\'{1}\''.format(bn.name, sec.name), file=stream)
                    if sec.common_name not in bn.common_names:
                        bn.common_names.append(sec.common_name)
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
        self.directory = current_app.config.get('PLANT_IMAGES_FOLDER')

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
        return os.path.exists(self.savepath)

    def save(self):
        """Save thumbnail as `parent.thumbnail` and add to images.

        Returns:
            Image: The `Image` to be set as a thumbnail.
        """
        if not self.exists():
            self.download()
        img = Image.query.filter(Image.filename == self.filename).one_or_none()
        if img:
            return img
        else:
            return Image(filename=self.filename)
