from bs4 import BeautifulSoup, Comment
import requests

from app.db_helpers import dbify


def first_text(tag):
    return next(
        (c for c in tag.contents if isinstance(c, str) and c.strip()),
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
    sections = [
        SectionTag(s) for s in tag.find_all('section', recursive=False)
    ]
    classes = [s.class_ for s in sections]
    dupes = [c for c in classes if classes.count(c) > 1]
    for dupe in dupes:
        secs = [s for s in sections if s.class_ == dupe]
        master = next((s for s in secs if s.intro), secs[0])
        secs.remove(master)
        for sec in secs:
            master.append(sec.children)
            sections.remove(sec)
            sec.extract()
    return sections


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
        self.h3 = tag.find('h3')
        self.h3_ems = self.h3.find_all('em')
        self.ps = tag.find_all('p')
        self.buttons = tag.find_all('button')

    def populate_d(self):
        self.d['name'] = first_text(self.h3)
        self.d['h3 ems'] = [first_text(em) for em in self.h3_ems]
        self.d['ps'] = [str(p) for p in self.ps]
        self.d['buttons'] = [parse_button(b) for b in self.buttons]

class SectionTag:
    def __init__(self, tag):
        self.tag = tag
        self.subsections = get_subsections(tag)
        self.header = self.tag.find(
            'div',
            class_=lambda x: x and x.lower() == 'section' or
            x.lower() == 'series'
        )
        self.cultivars = get_cultivars(tag)
        self.comments = extract_comments(tag)

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
        self.intro = self.main.find('div', class_='Introduction')
        self.comments = extract_comments(self.main)
