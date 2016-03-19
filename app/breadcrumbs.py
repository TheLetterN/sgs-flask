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


from flask import url_for
from titlecase import titlecase


class Crumbler(object):
    def __init__(self, blueprint):
        self.blueprint = blueprint

    def crumble(self, route, title=None, **kwargs):
        if not title:
            title = titlecase(route.replace('_', ' '))
        url = url_for('.'.join([self.blueprint, route]), **kwargs)
        return '<a href="{0}">{1}</a>'.format(url, title)

    def crumble_routes(self, routes, **kwargs):
        for route in routes:
            if isinstance(route, str):
                yield self.crumble(route, **kwargs)
            else:
                yield self.crumble(route[0], route[1], **kwargs)

    def crumble_route_group(self, route, route_group):
        if route not in route_group:
            raise ValueError('route must be in route_group!')
        routes = []
        for rt in route_group:
            routes.append(rt)
            if rt == route:
                break
        return self.crumble_routes(routes)
