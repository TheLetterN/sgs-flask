import json
import os
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from inflection import pluralize
import requests
from slugify import slugify
from werkzeug import secure_filename

from app import db
from app.db_helpers import dbify
from app.seeds.models import (
    BulkCategory,
    BulkItem,
    BulkSeries,
    CommonName,
    Cultivar,
    Image,
    Index,
    Packet,
    Section
)


STATIC = Path(Path.cwd(), 'app', 'static')


related_links = []


def str_contents(tag):
    try:
        return ' '.join(''.join(str(c) for c in tag.contents).split())
    except AttributeError:
        return None


def first_text(tag):
    if isinstance(tag, str):
        return tag
    try:
        return next(
            (c for c in tag.contents if isinstance(c, str) and
                not isinstance(c, Comment) and
                c.strip()),
            ''
        ).strip()
    except AttributeError:
        return ''


def extract_comments(tag):
    return '\n'.join(
        c.extract() for c in tag.find_all(
            text=lambda x: isinstance(x, Comment),
            recursive=False
        )
    )


def orblank(var):
    return var if var else ''


def tags_to_str(tags):
    return '\n'.join(str(t) for t in tags).replace('\r', '').replace('\t', '')


def get_subsections(tag):
    sections = tag.find_all('section', recursive=False)
    classes = [s['class'] for s in sections]
    dupes = []
    for c in classes:
        if classes.count(c) > 1 and c not in dupes:
            dupes.append(c)
    for dupe in dupes:
        secs = [s for s in sections if s['class'] == dupe]
        # If it has an h2, it's displayed.
        master = next((s for s in secs if s.h2), secs[0])
        secs.remove(master)
        for sec in secs:
            for s in sec.find_all('section', recursive=False):
                master.append(s.extract())
            for div in sec.find_all('div', recursive=False):
                master.append(div.extract())
            sections.remove(sec)
    return [SectionTag(s) for s in sections]


def get_cultivars(tag):
    return [
        CultivarTag(c) for c in tag.find_all(
            'div',
            class_='Cultivar',
            id=lambda x: x != 'heirloom-tomato-intro',
            recursive=False
        )
    ]


def parse_button(button):
    return {
        k.replace('data-item-', ''): button[k] for k in button.attrs
        if 'data-item' in k
    }


def clean_title(title):
    return dbify(title.lower().replace('seeds', '').strip())


def scrape_index(url):
    print('Scraping index from {} ...'.format(url))
    idx = IndexScraper(url)
    idx.create_dbdict()
    return idx


def save_index(idx, filename=None):
    print('Saving {} index...'.format(idx.dbdict['slug']))
    if not filename:
        p = Path('/tmp', '{}.json'.format(idx.dbdict['slug']))
    else:
        p = Path(filename)
    with p.open('w', encoding='utf-8') as ofile:
        ofile.write(idx.json)
    for cn in idx.dbdict['common_names']:
        for rl in cn['related_links']:
            related_links.append({
                'source': {
                    'idx_slug': idx.dbdict['slug'],
                    'cn_slug': cn['slug']
                },
                'target': rl
            })
    print('Saved {} to: {}'.format(idx.dbdict['slug'], p))


def load_index(slug, filename=None):
    if not filename:
        p = Path('/tmp', '{}.json'.format(slug))
    else:
        p = Path(filename)
    with p.open('r', encoding='utf-8') as ifile:
        return json.loads(ifile.read())


def download_image(url):
    relname = Path(*url.replace('//', '').split('/')[1:])
    fullname = Path(STATIC, relname.parent, secure_filename(relname.name))
    if fullname.exists():
        print('Image {} already exists, skipping download.'.format(fullname))
    else:
        print('Downloading {} and saving to "{}"...'.format(url, fullname))
        img_file = requests.get(url)
        if img_file.status_code == 200:
            fullname.parent.mkdir(parents=True, exist_ok=True)
            with fullname.open('wb') as ofile:
                ofile.write(img_file.content)
        else:
            try:
                img_file.raise_for_status()
            except requests.HTTPError as e:
                with open('/tmp/404.log', 'a', encoding='utf-8') as ofile:
                    ofile.write('{}\n'.format(e))
    img = Image.get_or_create(filename=str(relname))
    return img


def scrape_annuals():
    return scrape_index(
        'https://www.swallowtailgardenseeds.com/annualsA-Z.html'
    )


def save_annuals(ann=None, filename=None):
    if not ann:
        ann = scrape_annuals()
    save_index(ann, filename=filename)


def load_annuals(filename=None):
    return load_index('annuals', filename=filename)


def scrape_perennials():
    return scrape_index(
        'https://www.swallowtailgardenseeds.com/perennialsA-Z.html'
    )


def load_perennials(filename=None):
    return load_index('perennials', filename=filename)


def save_perennials(per=None, filename=None):
    if not per:
        per = scrape_perennials()
    save_index(per, filename=filename)


def scrape_vines():
    return scrape_index('https://www.swallowtailgardenseeds.com/vines/')


def save_vines(vin=None, filename=None):
    if not vin:
        vin = scrape_vines()
    save_index(vin, filename=filename)


def load_vines(filename=None):
    return load_index('vines', filename=filename)


def scrape_vegetables():
    return scrape_index('https://www.swallowtailgardenseeds.com/vegetables/')


def save_vegetables(veg=None, filename=None):
    if not veg:
        veg = scrape_vegetables()
    save_index(veg, filename=filename)


def load_vegetables(filename=None):
    return load_index('vegetables', filename=filename)


def scrape_herbs():
    return scrape_index('https://www.swallowtailgardenseeds.com/herbs/')


def save_herbs(herb=None, filename=None):
    if not herb:
        herb = scrape_herbs()
    save_index(herb, filename=filename)


def load_herbs(filename=None):
    return load_index('herbs', filename=filename)


def scrape_bulk():
    b = BulkScraper()
    b.create_dblist()
    return b


def save_bulk(bulk=None, filename=None):
    print('Saving bulk...')
    if not bulk:
        bulk = scrape_bulk()
    if not filename:
        filename = '/tmp/bulk.json'
    p = Path(filename)
    with p.open('w', encoding='utf-8') as ofile:
        ofile.write(json.dumps(bulk.dblist, indent=4))
    print('Bulk saved to: {}'.format(p))


def load_bulk(filename=None):
    if not filename:
        filename = '/tmp/bulk.json'
    p = Path(filename)
    with p.open('r', encoding='utf-8') as ifile:
        return json.loads(ifile.read())


def save_all():
    save_annuals()
    save_perennials()
    save_vines()
    save_vegetables()
    save_herbs()
    save_bulk()
    print('Saving related links...')
    with open('/tmp/related_links.json', 'w', encoding='utf-8') as ofile:
        ofile.write(json.dumps(related_links, indent=4))


def load_all():
    """Load all indexes from json files.

    Note: bulk is excluded because it operates differently, so should be
    handled on its own.
    """
    return (
        load_annuals(),
        load_perennials(),
        load_vines(),
        load_vegetables(),
        load_herbs()
    )


def add_index_to_database(d):
    print('Adding index {} to the database...'.format(d['name']))
    idx = Index.get_or_create(d['name'])
    db.session.add(idx)
    db.session.flush()
    idx.slug = d['slug']
    idx.description = d['description']
    if 'annual' in idx.slug:
        idx.thumbnail = download_image(
            'https://www.swallowtailgardenseeds.com/images/index-image-links'
            '/annual-flower-seeds4.jpg'
        )
    elif 'perennial' in idx.slug:
        idx.thumbnail = download_image(
            'https://www.swallowtailgardenseeds.com/images/index-image-links'
            '/perennial-flower-seeds.jpg'
        )
    elif 'vine' in idx.slug:
        idx.thumbnail = download_image(
            'https://www.swallowtailgardenseeds.com/images/index-image-links'
            '/flowering-vine-seeds2.jpg'
        )
    elif 'vegetable' in idx.slug:
        idx.thumbnail = download_image(
            'https://www.swallowtailgardenseeds.com/images/index-image-links'
            '/vegetable-seeds2.jpg'
        )
    elif 'herb' in idx.slug:
        idx.thumbnail = download_image(
            'https://www.swallowtailgardenseeds.com/images/index-image-links'
            '/herb-seeds2.jpg'
        )
    idx.common_names = list(generate_common_names(idx, d['common_names']))
    db.session.flush()
    idx.common_names = sorted(idx.common_names, key=lambda x: x.list_as)
    idx.common_names.reorder()
    db.session.commit()
    print('Finished adding {} to the database.'.format(d['name']))


def add_bulk_to_database(l):
    for d in l:
        print('Adding bulk category "{}" to database...'.format(d['header']))
        cat = BulkCategory.get_or_create(d['slug'])
        db.session.add(cat)
        cat.name = d['header']  # Deal with it.
        cat.subtitle = d['subtitle']
        cat.list_as = d['list_as']
        cat.items = list(generate_bulk_items(cat, d['items']))
        # series after items so items in series end up in items.
        cat.series = list(generate_bulk_series(cat, d['sections']))
        db.session.flush()
        cat.series.reorder()
        cat.items.reorder()
        db.session.commit()
        print('Finished adding "{}" to database.'.format(cat.name))
    download_image(
        'https://www.swallowtailgardenseeds.com/images/index-image-links/'
        'bulk-catalog3.jpg'
    )
    print('Finished adding bulk to database.')


def generate_bulk_series(cat, l):
    for d in l:
        ser = BulkSeries.get_or_create(cat, d['slug'])
        db.session.add(ser)
        ser.name = d['name']
        ser.subtitle = d['subtitle']
        if d['thumbnail']:
            ser.thumbnail = download_image(d['thumbnail'])
        ser.items = list(generate_bulk_items(cat, d['items']))
        db.session.flush()
        ser.items.reorder()
        yield ser


def generate_bulk_items(cat, l):
    for d in l:
        item = BulkItem.get_or_create(cat, d['slug'])
        db.session.add(item)
        item.name = d['name']
        item.product_name = d['product_name']
        item.sku = d['sku']
        item.price = d['price']
        item.taxable = d['taxable']
        yield item


def generate_common_names(idx, l):
    for d in l:
        cn = CommonName.get_or_create(d['name'], idx)
        db.session.add(cn)
        cn.list_as = d['list_as']
        cn.slug = d['slug']
        cn.subtitle = d['subtitle']
        cn.sunlight = d['sunlight']
        cn.thumbnail = download_image(d['thumb_url'])
        cn.botanical_names = d['botanical_names']
        cn.description = d['description']
        cn.instructions = d['instructions']
        if not cn.cultivars:
            cn.cultivars = []
        for cv in generate_cultivars(cn, d['cultivars']):
            if cv not in cn.cultivars:
                cn.cultivars.append(cv)
        if not cn.sections:
            cn.sections = []
        for s in generate_sections(cn, d['sections']):
            if s not in cn.sections:
                cn.sections.append(s)
        db.session.flush()
        cn.child_sections.reorder()
        cn.child_cultivars.reorder()
        yield cn


def generate_sections(cn, l):
    for d in l:
        sec = Section.get_or_create(d['name'], cn)
        db.session.add(sec)
        sec.botanical_names = d['botanical_names']
        sec.subtitle = d['subtitle']
        sec.description = d['description']
        if d['thumbnail']:
            sec.thumbnail = download_image(d['thumbnail'])
        sec.cultivars = list(generate_cultivars(cn, d['cultivars']))
        sec.children = list(generate_sections(cn, d['subsections']))
        db.session.flush()
        sec.child_cultivars.reorder()
        sec.children.reorder()
        yield sec


def generate_cultivars(cn, l):
    for d in l:
        cv = Cultivar.get_or_create(d['name'], cn)
        db.session.add(cv)
        cv.visible = True
        cv.active = True
        cv.subtitle = d['subtitle']
        cv.botanical_name = d['botanical_names']
        cv.description = d['description']
        if d['veg_info']:
            if d['veg_info']['open_pollinated']:
                cv.open_pollinated = True
            if d['veg_info']['maturation']:
                cv.maturation = d['veg_info']['maturation']
        try:
            cv.new_for = int(d['new_for'])
        except ValueError:
            pass
        cv.featured = d['favorite']
        cv.favorite = d['favorite']
        cv.in_stock = d['packets'][0]['in_stock']
        if 'organic' in cv.description.lower():
            cv.organic = True
        cv.taxable = d['packets'][0]['taxable']
        cv.images = [download_image(i) for i in d['images']]
        cv.thumbnail = cv.images[0]
        cv.packets = list(generate_packets(d['packets']))
        yield cv


def generate_packets(l):
    for d in l:
        pkt = Packet.get_or_create(d['sku'])
        db.session.add(pkt)
        pkt.product_name = d['product_name']
        pkt.price = d['price']
        pkt.amount = d['amount']
        yield pkt


def set_related_links():
    with open('/tmp/related_links.json', 'r', encoding='utf-8') as ifile:
        dicts = json.loads(ifile.read())
        print('Setting related links/grows with...')
        for d in dicts:
            cn = CommonName.from_slugs(
                d['source']['idx_slug'],
                d['source']['cn_slug']
            )
            if d['target']['anchor']:
                t = Cultivar.from_slugs(
                    d['target']['idx_slug'],
                    d['target']['cn_slug'],
                    d['target']['anchor']
                )
                if t:
                    cn.gw_cultivars.append(t)
                else:
                    t = Section.from_slugs(
                        d['target']['idx_slug'],
                        d['target']['cn_slug'],
                        d['target']['anchor']
                    )
                    if t:
                        cn.gw_sections.append(t)
                    else:
                        print(
                            'Could not find a Section or Cultivar with the '
                            'slug: "{}"'.format(d['target']['anchor'])
                        )
                        t = CommonName.from_slugs(
                            d['target']['idx_slug'],
                            d['target']['cn_slug']
                        )
                        cn.gw_common_names.append(t)
            else:
                t = CommonName.from_slugs(
                    d['target']['idx_slug'],
                    d['target']['cn_slug']
                )
                if t:
                    cn.gw_common_names.append(t)
                else:
                    print('Could not find gw for {}'.format(d))
            if t:
                print(
                    '"{}" grows with the {} "{}"'
                    .format(cn.name, t.__class__.__name__, t.name)
                )
        db.session.commit()


def download_misc_images():
    """Download any images that are needed but not used in the db."""
    images = [
        'https://www.swallowtailgardenseeds.com/images/'
        'ben-about-us-thumbnail.jpg',
        'https://www.swallowtailgardenseeds.com/images/'
        'emily-about-us-thumbnail.jpg',
        'https://www.swallowtailgardenseeds.com/images/'
        'levon-about-us-tree-thumbnail.png',
        'https://www.swallowtailgardenseeds.com/images/'
        'levon-about-us-tree-thumbnail.png',
        'https://www.swallowtailgardenseeds.com/images/'
        'mary-about-us-thumbnail.jpg',
        'https://www.swallowtailgardenseeds.com/images/'
        'nicholas-about-us-tree-thumbnail.png',
        'https://www.swallowtailgardenseeds.com/images/ben-about-us.jpg',
        'https://www.swallowtailgardenseeds.com/images/emily-about-us.jpg',
        'https://www.swallowtailgardenseeds.com/images/'
        'levon-about-us-tree.png',
        'https://www.swallowtailgardenseeds.com/images/'
        'mary-about-us-morning-glory.jpg',
        'https://www.swallowtailgardenseeds.com/images/'
        'nicholas-about-us-tree.png'
    ]
    for image in images:
        download_image(image)


class CultivarTag:
    def __init__(self, tag):
        self.tag = tag
        self.images = tag.find_all('img')
        self.new_for = tag.find('span', class_='Cultivar_span_new')
        self.favorite = tag.find('span', class_='Cultivar_span_best_seller')
        self.h3 = tag.find('h3')
        try:
            self.h3_ems = self.h3.find_all('em')
        except AttributeError:
            raise RuntimeError(
                'An AttributeError was raised making tag for: {}'.format(self.tag)
            )
        try:
            self.subtitle_em = self.h3_ems[0]
        except IndexError:
            self.subtitle_em = None
        self.veg_em = None
        self.bn_em = None
        if len(self.h3_ems) > 1:
            em = self.h3_ems[1]
            if '(OP)' in em.text or 'days' in em.text:
                self.veg_em = em
            else:
                self.bn_em = em
            if len(self.h3_ems) == 3:
                for c in self.h3_ems[2].contents:
                    self.bn_em.append(c.extract())
            if len(self.h3_ems) > 3:
                raise RuntimeError(
                    'More than 3 ems dectected:\n{}'.format(self.h3_ems)
                )
        self.ps = tag.find_all('p')
        self.buttons = tag.find_all('button')
        self._dbdict = dict()

    def __repr__(self):
        return '<CultivarTag "{}">'.format(self.dbdict['name'])

    def get_packet_dicts(self):
        return [
            {
                'sku': b['data-item-id'],
                'amount': b['data-item-description'],
                'product_name': b['data-item-name'],
                'price': b['data-item-price'],
                'taxable': True if 't' in b['data-item-taxable'] else False,
                'in_stock': False if 'OUT' in b.text.upper() else True
            } for b in self.buttons
        ]

    @property
    def dbdict(self):
        if not self._dbdict:
            self.create_dbdict()
        return self._dbdict

    def create_dbdict(self):
        print('Creating dbdict for cultivar "{}"...'.format(self.h3))
        self._dbdict['name'] = first_text(self.h3)
        self._dbdict['subtitle'] = first_text(self.subtitle_em)
        self._dbdict['botanical_names'] = first_text(self.bn_em)
        self._dbdict['description'] = tags_to_str(self.ps)
        self._dbdict['new_for'] = '2017' if self.new_for else ''
        self._dbdict['favorite'] = True if self.favorite else False
        self._dbdict['images'] = [
            i['src'].replace('\n', '') for i in self.images
        ]
        self._dbdict['packets'] = self.get_packet_dicts()
        self._dbdict['veg_info'] = {}
        if self.veg_em:
            abbrs = self.veg_em.find_all('abbr')
            self._dbdict['veg_info']['open_pollinated'] = False
            for abbr in abbrs:
                abbr.extract()
                if '(OP)' in abbr.text:
                    self._dbdict['veg_info']['open_pollinated'] = True
            self._dbdict['veg_info']['maturation'] = str_contents(self.veg_em)
        try:
            self._dbdict['slug'] = slugify(self.tag['id'])
        except KeyError:
            try:
                self._dbdict['slug'] = slugify(self.h3['id'])
            except KeyError:
                try:
                    self._dbdict['slug'] = slugify(self.tag.img['id'])
                except KeyError:
                    self._dbdict['slug'] = None


class SectionTag:
    def __init__(self, tag):
        self.tag = tag
        self.subsections = get_subsections(tag)
        self.header = self.tag.find(
            'div',
            class_=lambda x: x and x.lower() == 'section' or
            x.lower() == 'series'
        )
        if self.header:
            self.header_h2 = self.header.find('h2')
            self.header_ems = self.header_h2.find_all('em')
            if len(self.header_ems) == 1:
                self.subtitle = self.header_h2.find(
                    'em',
                    class_=lambda x: x and 'Series_em' in x
                )
                self.botanical_names = self.header_h2.find(
                    'em',
                    class_=lambda x: x and 'Section_em' in x
                )
            elif len(self.header_ems) > 1:
                self.subtitle = self.header_ems[0]
                self.botanical_names = self.header_ems[1]
            else:
                self.subtitle = None
                self.botanical_names = None
            self.intro = self.header.find_all('p') if self.header else ''
            related = self.tag.find_previous(
                'div',
                class_='RelatedLinks'
            )
            try:
                a = related.find(
                    'a',
                    href=lambda x: self.header['id'].lower() in x.lower()
                )
                self.thumbnail = a.find('img')
            except (AttributeError, KeyError):
                self.thumbnail = None

        else:
            c = self.tag['class'][0].replace('-', ' ').replace('seeds', '')
            self.header_h2 = c.title().strip()
            self.botanical_names = ''
            self.intro = ''
            self.subtitle = ''
            self.thumbnail = None
            
        self.cultivars = get_cultivars(tag)
        self.comments = extract_comments(tag)
        self._dbdict = dict()

    def __repr__(self):
        return '<SectionTag class="{}">'.format(self.class_)

    @property
    def dbdict(self):
        if not self._dbdict:
            self.create_dbdict()
        return self._dbdict

    @property
    def class_(self):
        return self.tag['class']

    @property
    def name(self):
        try:
            rawname = next(
                t for t in self.intro.h2.contents if isinstance(t, str) and
                not isinstance (t, Comment) and
                t.strip()
            )
        except AttributeError:
            rawname = ' '.join(
                self.class_.replace('section', '').split('-')
            ).strip()
        return dbify(rawname)

    def create_dbdict(self):
        print('Creating dbdict for section "{}"...'.format(self.header_h2))
        self._dbdict['name'] = first_text(self.header_h2)
        self._dbdict['subtitle'] = first_text(self.subtitle)
        self._dbdict['botanical_names'] = first_text(self.botanical_names)
        self._dbdict['description'] = tags_to_str(self.intro)
        self._dbdict['subsections'] = [s.dbdict for s in self.subsections]
        self._dbdict['cultivars'] = [c.dbdict for c in self.cultivars]
        try:
            self._dbdict['slug'] = slugify(self.header['id'])
        except (AttributeError, KeyError, TypeError):
            self._dbdict['slug'] = None
        try:
            self._dbdict['thumbnail'] = self.thumbnail['src']
        except (TypeError, KeyError):
            self._dbdict['thumbnail'] = None


class IndexScraper:
    """A scraper for an index (category) page."""
    def __init__(self, url):
        self.url = url
        r = requests.get(url)
        r.encoding = 'utf-8'
        self.soup = BeautifulSoup(r.text, 'html5lib')
        self.main = self.soup.find('div', id='main')
        if not self.main:
            raise RuntimeError('No main div on index page: {}'.format(url))
        self.h1 = self.main.find('h1')
        self.links = self.main.find(
            'div',
            class_='Index_pages-image-links-wrapper'
        ).find_all('a')
        self.link_urls = [a['href'] for a in self.links]
        self.intro = self.main.find_all('p', class_='Index_pages-intro')
        self.intro += self.main.find_all(
            'blockquote',
            class_='Index_pages-blockquote'
        )
        self.intro += self.main.find_all(
            'i',
            class_='Index_pages-blockquote-i'
        )
        self._common_names = None
        self._dbdict = dict()

    @property
    def common_names(self):
        if not self._common_names:
            print('Scraping common name pages...')
            self._common_names = []
            for l in self.links:
                url = l['href']
                thumb = l.find('img')['src']
                print('Scraping {}...'.format(url))
                self._common_names.append(CNScraper(url, thumb))
        return self._common_names

    @property
    def dbdict(self):
        if not self._dbdict:
            self.create_dbdict()
        return self._dbdict

    @property
    def json(self):
        return json.dumps(self.dbdict, indent=4)

    def create_dbdict(self):
        print('Creating dbdict for "{}"...'.format(self.url))
        name = clean_title(first_text(self.h1))
        self._dbdict['name'] = name
        if 'annual' in name.lower():
            slug = 'annuals'
        elif 'perenn' in name.lower():
            slug = 'perennials'
        elif 'vine' in name.lower():
            slug = 'vines'
        elif 'veg' in name.lower():
            slug = 'vegetables'
        elif 'herb' in name.lower():
            slug = 'herbs'
        else:
            raise ValueError('Could not determine slug for "{}"'.format(name))
        self._dbdict['slug'] = slug
        self._dbdict['description'] = tags_to_str(self.intro)
        self._dbdict['common_names'] = [
            c.dbdict for c in self.common_names
        ]


class CNScraper:
    """A scraper for a given common name page."""
    def __init__(self, url, thumbnail=None):
        self.url = url
        self.thumbnail = thumbnail
        r = requests.get(url)
        r.encoding = 'utf-8'
        self.soup = BeautifulSoup(r.text, 'html5lib')
        self.main = self.soup.find('div', id='main')
        if not self.main:
            raise RuntimeError('No main div on CN page: {}'.format(url))
        self.sections = get_subsections(self.main)
        self.cultivars = get_cultivars(self.main)
        self.header = self.main.find('div', class_='Header')
        self.header_h1 = self.header.find('h1')
        self.header_h2 = self.header.find('h2')
        self.header_h3 = self.header.find('h3')
        self.sun = self.header.find(
            'p',
            class_=lambda x: x and 'sun' in x or 'shade' in x
        )
        self.intro = self.main.find('div', class_='Introduction')
        self.comments = extract_comments(self.main)
        self.growing_divs = self.main.find_all('div', class_='Growing')
        self.growing = self.growing_divs[-1] if self.growing_divs else None
        self.sidenav = self.soup.find('div', class_='Sidebar')
        self.sn_link = self.sidenav.find_all('a', href=self.url)[-1]
        try:
            self.growing.h2.extract()
        except AttributeError:
            pass
        self.onpage_nav = None
        self.related_links = None
        self.parse_related_and_nav()
        self.consolidate_cultivars()
        self._dbdict = dict()

    def __repr__(self):
        return '<CNScraper url="{}">'.format(self.url)

    @property
    def dbdict(self):
        if not self._dbdict:
            self.create_dbdict()
        return self._dbdict

    def create_dbdict(self):
        print('Creating dbdict for "{}"...'.format(self.url))
        self._dbdict['name'] = clean_title(first_text(self.header_h1))
        self._dbdict['list_as'] = self.sn_link.text.strip()
        try:
            self._dbdict['description'] = tags_to_str(self.intro.contents)
        except AttributeError:
            self._dbdict['description'] = ''
        heirloom = self.main.find('div', id='heirloom-tomato-intro')
        if heirloom:
            self._dbdict['description'] = str(heirloom)
        self._dbdict['subtitle'] = str_contents(self.header_h2)
        self._dbdict['botanical_names'] = str_contents(self.header_h3)
        self._dbdict['slug'] = self.url.split('/')[-1].replace('.html', '')
        try:
            self._dbdict['sunlight'] = next(
                c for c in self.sun['class'] if 'sun' in c or 'shade' in c
            )
        except TypeError:
            self._dbdict['sunlight'] = ''
        self._dbdict['thumb_url'] = self.thumbnail
        try:
            self._dbdict['instructions'] = tags_to_str(
                self.growing.contents
            )
        except AttributeError:
            self._dbdict['instructions'] = ''
        self._dbdict['sections'] = [s.dbdict for s in self.sections]
        self._dbdict['cultivars'] = [c.dbdict for c in self.cultivars]
        self._dbdict['related_links'] = list(
            generate_related_links_dicts(self.related_links)
        )

    def parse_related_and_nav(self):
        rls = self.main.find_all('div', class_='RelatedLinks')
        if len(rls) > 2:
            raise ValueError(
                'Found more than two RelatedLinks divs on {}!'.format(self.url)
            )
        for rl in rls:
            if 'navigation' in rl['class']:
                self.onpage_nav = rl
            else:
                self.related_links = rl

    def consolidate_cultivars(self):
        for s in self.sections:
            c = ' '.join(s.class_).lower()
            if 'individual' in c and 'variet' in c:
                self.cultivars += s.cultivars
                self.sections.remove(s)

    @property
    def all_cultivars(self):
        cultivars = list(self.cultivars)
        for section in self.sections:
            cultivars += section.cultivars
            for sec in section.subsections:
                cultivars += sec.cultivars
        return cultivars


def get_links(tag, *args, **kwargs):
    try:
        return [a['href'] for a in tag.find_all('a', *args, **kwargs)]
    except AttributeError:
        return []


def generate_related_links_dicts(tag):
    links = get_links(tag)
    for link in links:
        parts = link.split('/')[-2:]
        more_parts = parts[1].split('#')
        yield {
            'idx_slug': parts[0],
            'cn_slug': more_parts[0].replace('.html', ''),
            'anchor': slugify(more_parts[1]) if len(more_parts) == 2 else None
        }


class BulkScraper:
    """A scraper for the bulk section."""
    def __init__(self):
        self.url = 'https://www.swallowtailgardenseeds.com/bulk/'
        r = requests.get(self.url)
        r.encoding = 'utf-8'
        self.soup = BeautifulSoup(r.text, 'html5lib')
        self.ul = self.soup.find('ul', class_='bulk-index')
        self.links = self.ul.find_all('a')
        self._dblist = []

    @property
    def dblist(self):
        if not self._dblist:
            self.create_dblist()
        return self._dblist

    def create_dblist(self):
        print('Creating Bulk dblist...')
        self._dblist = [BulkPage(l).dbdict for l in self.links]


class BulkPage:
    """A scraped page in the bulk section."""
    def __init__(self, link):
        self.url = link['href']
        self.list_as = link.text
        r = requests.get(self.url)
        r.encoding = 'utf-8'
        self.soup = BeautifulSoup(r.text, 'html5lib')
        self.h1 = self.soup.find('h1')
        self.h2 = self.soup.find('h2', class_='Header_h2')
        self.section_divs = self.soup.find_all('div', class_='Series')
        try:
            self.section_links = self.soup.find(
                'div',
                class_='RelatedLinks'
            ).find_all('a')
        except AttributeError:
            self.section_links = []
        self.section_thumbs = {
            a['href'][1:] : a.find('img')['src'] for a in self.section_links
        }
        self.sections = [
            {
                'div': d,
                'thumbnail': self.get_section_thumb(d['id']),
                'table': d.find_next('table'),
                'rows': d.find_next('table').find_all('tr')
            } for d in self.section_divs
        ]
        self.tables = [
            t for t in self.soup.find_all(
                'table', class_='bulk-items'
            ) if t not in (
                s['table'] for s in self.sections
            )
        ]
        self.rows = []
        for t in self.tables:
            self.rows += t.find_all('tr')
        self._dbdict = dict()

    @property
    def dbdict(self):
        if not self._dbdict:
            self.create_dbdict()
        return self._dbdict

    def get_section_thumb(self, section_id):
        try:
            return self.section_thumbs[section_id]
        except KeyError:
            return None

    def create_dbdict(self):
        def item_from_row(row):
            button = row.find('button')
            taxable = False if 'f' in button['data-item-taxable'] else True
            name = ' '.join(row.find('td').text.strip().split())

            return {
                'name': name,
                'slug': slugify(name),
                'sku': button['data-item-id'],
                'product_name': button['data-item-name'],
                'price': button['data-item-price'],
                'taxable': taxable
            }
        def dict_from_section(sec):
            return {
                'name': ' '.join(first_text(sec['div'].find('h2')).split()),
                'slug': sec['div']['id'],
                'subtitle': sec['div'].find('em').text.strip(),
                'thumbnail': sec['thumbnail'],
                'items': [item_from_row(r) for r in sec['rows']]
            }
        header = ' '.join(self.h1.text.strip().split())
        subtitle = ' '.join(self.h2.text.strip().split()) if self.h2 else None
        print('Creating dbdict for {}...'.format(header))
        self._dbdict = {
            'list_as': self.list_as,
            'header': header,
            'subtitle': subtitle,
            'slug': self.url.split('/')[-1].replace('.html', ''),
            'sections': [dict_from_section(s) for s in self.sections],
            'items': [item_from_row(r) for r in self.rows]
        }
