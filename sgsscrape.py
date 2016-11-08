import json
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from inflection import pluralize
import requests

from app import db
from app.db_helpers import dbify
from app.seeds.models import (
    CommonName,
    Cultivar,
    Image,
    Index,
    Section
)


STATIC = Path(Path.cwd(), 'app', 'static')


def first_text(tag):
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
    return '\n'.join(str(t) for t in tags)


def get_subsections(tag):
    sections = tag.find_all('section', recursive=False)
    classes = [s['class'] for s in sections]
    dupes = []
    for c in classes:
        if classes.count(c) > 1 and c not in dupes:
            dupes.append(c)
    for dupe in dupes:
        secs = [s for s in sections if s['class'] == dupe]
        # If it has a <p> tag in it, it's got an intro. Probably.
        master = next((s for s in secs if s.find('p')), secs[0])
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
        CultivarTag(c) for c in tag.find_all('div',
                                             class_='Cultivar',
                                             id=lambda x: x != 'heirloom-tomato-intro',
                                             recursive=False)
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


def save_index(idx):
    print('Saving {} index...'.format(idx.dbdict['slug']))
    p = Path('/tmp', '{}.json'.format(idx.dbdict['slug']))
    with p.open('w', encoding='utf-8') as ofile:
        ofile.write(idx.json)
    print('Saved {} to: {}'.format(idx.dbdict['slug'], p))


def download_image(url):
    relname = Path(*url.replace('//', '').split('/')[1:])
    fullname = Path(STATIC, relname)
    if fullname.exists():
        print('Image {} already exists, skipping download.')
    else:
        print('Downloading {} and saving to "{}"...'.format(url, fullname))
        img_file = requests.get(url)
        if img_file.status_code == 200:
            fullname.parent.mkdir(parents=True, exist_ok=True)
            with fullname.open('wb') as ofile:
                ofile.write(img_file.content)
        else:
            img_file.raise_for_status()
    img = Image.get_or_create(filename=str(relname))
    db.session.add(img)
    return img


def scrape_annuals():
    return scrape_index(
        'https://www.swallowtailgardenseeds.com/annualsA-Z.html'
    )


def save_annuals(ann=None):
    if not ann:
        ann = scrape_annuals()
    save_index(ann)


def scrape_perennials():
    return scrape_index(
        'https://www.swallowtailgardenseeds.com/perennialsA-Z.html'
    )


def save_perennials(per=None):
    if not per:
        per = scrape_perennials()
    save_index(per)


def scrape_vines():
    return scrape_index('https://www.swallowtailgardenseeds.com/vines/')


def save_vines(vin=None):
    if not vin:
        vin = scrape_vines()
    save_index(vin)


def scrape_vegetables():
    return scrape_index('https://www.swallowtailgardenseeds.com/vegetables/')


def save_vegetables(veg=None):
    if not veg:
        veg = scrape_vegetables()
    save_index(veg)


def scrape_herbs():
    return scrape_index('https://www.swallowtailgardenseeds.com/herbs/')


def save_herbs(herb=None):
    if not herb:
        herb = scrape_herbs()
    save_index(herb)


def add_index_to_database(d):
    print('Adding index {} to the database...'.format(d['name']))
    idx = Index.get_or_create(d['name'])
    db.session.add(idx)
    db.session.flush()
    idx.slug = d['slug']
    idx.description = d['description']
    for cn in d['common_names']:
        add_common_name_to_database(idx, cn)
    db.session.commit()


def add_common_name_to_database(idx, d):
    print('Adding common name {} to the database...'.format(d['name']))
    cn = CommonName.get_or_create(d['name'], idx)
    db.session.add(cn)
    cn.slug = d['slug']
    cn.subtitle = d['subtitle']
    cn.sunlight = d['sunlight']
    cn.thumbnail = download_image(d['thumb_url'])
    cn.botanical_names = d['botanical_names']
    cn.description = d['description']
    cn.instrictions = d['instructions']
    for sec in d['sections']:
        add_section_to_database(cn, sec)


def add_section_to_database(cn, d, parent=None):
    sec = Section.get_or_create(d['name'], cn)
    db.session.add(sec)
    sec.parent = parent
    sec.botanical_names = d['botanical_names']
    sec.subtitle = d['subtitle']
    sec.description = d['description']
    for s in d['subsections']:
        add_section_to_database(cn, s, sec)


def add_cultivar_to_database(cn, d, section=None):
    cv = Cultivar.get_or_create(cn, d['name'])
    db.session.add(cv)
    if section:
        section.cultivars.append(cv)
    cv.slug = d['slug']
    cv.subtitle = d['subtitle']
    cv.botanical_name = d['botanical_names']
    cv.description = d['description']
    #TODO: new_until
    cv.featured = d['favorite']
    #TODO: in_stock
    #TODO: organic
    cv.taxable = d['packets'][0]['taxable']
    cv.images = [download_image(i) for i in d['images']]
    cv.thumbnail = cv.images[0]
    for p in d['packets']:
        add_packet_to_database(cv, p)


def add_packet_to_database(cv, d):
    pkt = Packet.get_or_create(d['sku'])
    db.session.add(pkt)
    if pkt not in cv.packets:
        cv.packets.append(pkt)
    #TODO: finish this


class CultivarTag:
    def __init__(self, tag):
        self.tag = tag
        self.images = tag.find_all('img')
        self.new_for = tag.find('span', class_='Cultivar_span_new')
        self.favorite = tag.find('span', class_='Cultivar_span_best_seller')
        self.h3 = tag.find('h3')
        self.h3_ems = self.h3.find_all('em')
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
                'taxable': True if 't' in b['data-item-taxable'] else False
            } for b in self.buttons
        ]

    @property
    def dbdict(self):
        if not self._dbdict:
            self.create_dbdict()
        return self._dbdict

    @property
    def veg_op(self):
        return self.veg_em and 'OP' in str(self.veg_em)

    @property
    def veg_dtm(self):
        if self.veg_em and 'days' in str(self.veg_em):
            return next(
                s for s in str(self.veg_em) if any(c.isdigit() for c in s)
            )
        return None

    def create_dbdict(self):
        print('Creating dbdict for cultivar "{}"...'.format(self.h3))
        self._dbdict['name'] = first_text(self.h3)
        self._dbdict['subtitle'] = first_text(self.subtitle_em)
        self._dbdict['botanical_names'] = first_text(self.bn_em)
        self._dbdict['description'] = tags_to_str(self.ps)
        self._dbdict['new_for'] = '2017' if self.new_for else ''
        self._dbdict['favorite'] = True if self.favorite else False
        self._dbdict['images'] = [i['src'] for i in self.images]
        self._dbdict['packets'] = self.get_packet_dicts()
        self._dbdict['open_pollinated'] = self.veg_op
        self._dbdict['days_to_maturity'] = self.veg_dtm


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
        else:
            self.header_h2 = str(self.tag['class'])
            self.botanical_names = ''
            self.intro = ''
            self.subtitle = ''
            
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
        try:
            self._dbdict['description'] = tags_to_str(self.intro.contents)
        except AttributeError:
            self._dbdict['description'] = ''
        self._dbdict['subtitle'] = first_text(self.header_h2)
        self._dbdict['botanical_names'] = first_text(self.header_h3)
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
        try:
            self._dbdict['related_links'] = [
                a['href'] for a in self.related_links
            ]
        except TypeError:
            self._dbdict['related_links'] = []
        self._dbdict['sections'] = [s.dbdict for s in self.sections]
        self._dbdict['cultivars'] = [c.dbdict for c in self.cultivars]

    def parse_related_and_nav(self):
        rls = self.main.find_all('div', class_='RelatedLinks')
        if len(rls) > 2:
            raise ValueError(
                'Found more than two RelatedLinks divs on {}!'.format(self.url)
            )
        for rl in rls:
            if rl.find('a', href=lambda x: x[0] == '#'):
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
