from bs4 import BeautifulSoup, Comment
import requests

from app.db_helpers import dbify


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


class CultivarTag:
    def __init__(self, tag):
        self.tag = tag


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
        hp = self.main.find('p', class_='Header_p')
        self.sunlight = next(
            (c for c in hp['class'] if 'sun' in c or 'shade' in c),
            None
        )
        subh2 = self.main.find('h2', class_='Header_h2')
        self.subtitle = subh2.text if subh2 else ''
        subh3 = self.main.find('h3', class_='Header_h3')
        self.botanical_names = subh3.text if subh3 else ''
