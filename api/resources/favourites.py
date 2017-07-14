from datetime import datetime

from flask import json
from flask_restful import Resource, reqparse, marshal_with

from api.app import db
from api.common.models import History, Token, Manga, Favourite
from api.common.schemas import history_schema, favourites_schema

parser = reqparse.RequestParser()
parser.add_argument('X-AuthToken', location='headers')
parser.add_argument('updated')
parser.add_argument('deleted')


class FavouritesApi(Resource):
	@marshal_with(favourites_schema)
	def get(self):
		try:
			args = parser.parse_args()
			token = Token.query.get(args['X-AuthToken'])
			if token is None:
				return {'state': 'fail', 'message': 'Invalid token'}, 403
			user = token.user
			favourites = Favourite.query.filter(Favourite.user_id == user.id).all()
			return {'all': favourites}
		except Exception as e:
			return {'state': 'fail', 'message': str(e)}, 500

	@marshal_with(favourites_schema)
	def post(self):
		try:
			args = parser.parse_args()
			token = Token.query.get(args['X-AuthToken'])
			if token is None:
				return {'state': 'fail', 'message': 'Invalid token'}, 403
			user = token.user
			last_sync = token.last_sync_favourites
			favourites = Favourite.query.filter(Favourite.user_id == user.id)
			if last_sync is not None:
				favourites = favourites.filter(Favourite.updated_at > last_sync)
			updated = favourites.all()

			client_updated = json.loads(args['updated'])

			for item in client_updated:
				item['updated_at'] = datetime.fromtimestamp(item['timestamp'] / 1000.0)
				item.pop('timestamp', None)
				obj = Favourite(**item)
				obj.manga = Manga(**item['manga'])
				obj.user_id = user.id
				obj.manga_id = obj.manga.id
				manga = Manga.query.get(obj.manga_id)
				if manga is None:
					db.session.add(obj.manga)
					db.session.flush()
				fav = Favourite.query.filter(Favourite.manga_id == obj.manga_id, Favourite.user_id == obj.user_id).first()
				if fav is None:
					db.session.add(obj)
				else:
					fav.updated_at = obj.updated_at
				db.session.flush()

			token.last_sync_favourites = datetime.now()
			db.session.flush()
			db.session.commit()
			return {'updated': updated}
		except Exception as e:
			db.session.rollback()
			return {'state': 'fail', 'message': str(e)}, 500