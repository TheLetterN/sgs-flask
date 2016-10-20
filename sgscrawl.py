from bs4 import BeautifulSoup, Comment
import requests

from app.db_helpers import dbify


def first_text(tag):
    return next(
        (c for c in tag.contents if isinstance(c, str) and
            not isinstance(c, Comment) and
            c.strip()),
        ''
    ).strip()


def extract_comments(tag):
    return '\n'.join(
        c.extract() for c in tag.find_all(
            text=lambda x: isinstance(x, Comment),
            recursive=False
        )
    )


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
                                             recursive=False)
    ]


def parse_button(button):
    return {
        k.replace('data-item-', ''): button[k] for k in button.attrs
        if 'data-item' in k
    }


class CultivarTag:
    def __init__(self, tag):
        self.tag = tag
        self.d = dict()
        self.images = tag.find_all('img')
        self.new_for = tag.find('span', class_='Cultivar_span_new')
        self.favorite = tag.find('span', class_='Cultivar_span_best_seller')
        self.h3 = tag.find('h3')
        self.h3_ems = self.h3.find_all('em')
        self.ps = tag.find_all('p')
        self.buttons = tag.find_all('button')
        self.populate_d()

    def populate_d(self):
        self.d['name'] = first_text(self.h3)
        self.d['h3 ems'] = [first_text(em) for em in self.h3_ems]
        self.d['ps'] = [str(p) for p in self.ps]
        self.d['buttons'] = [parse_button(b) for b in self.buttons]

    def __repr__(self):
        return '<CultivarTag "{}">'.format(self.d['name'])

class SectionTag:
    def __init__(self, tag):
        self.tag = tag
        self.subsections = get_subsections(tag)
        self.header = self.tag.find(
            'div',
            class_=lambda x: x and x.lower() == 'section' or
            x.lower() == 'series'
        )
        self.intro = self.header.find_all('p') if self.header else None
        self.cultivars = get_cultivars(tag)
        self.comments = extract_comments(tag)

    def __repr__(self):
        return '<SectionTag class="{}">'.format(self.class_)

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
        


class CNCrawler:
    """A crawler for a given common name page."""
    def __init__(self, url):
        self.url = url
        r = requests.get(url)
        r.encoding = 'utf-8'
        self.soup = BeautifulSoup(r.text, 'html5lib')
        self.main = self.soup.find('div', id='main')
        if not self.main:
            raise RuntimeError('No main div found for page: {}'.format(url))
        self.sections = get_subsections(self.main)
        self.cultivars = get_cultivars(self.main)
        self.header = self.main.find('div', class_='Header')
        self.sun = self.header.find(
            'p',
            class_=lambda x: x and 'sun' in x or 'shade' in x
        )
        self.intro = self.main.find('div', class_='Introduction')
        self.comments = extract_comments(self.main)
        self.growing = self.main.find('div', class_='Growing')
        self.onpage_nav = None
        self.related_links = None
        self.parse_related_and_nav()
        self.consolidate_cultivars()

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
