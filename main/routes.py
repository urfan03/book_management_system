from flask import jsonify, request
from sqlalchemy.sql import exists
from .models import db, Book
from .google_books import import_books_by_author
from .functions import jsonify_object, query_string_filter, request_to_dict
from .exceptions import GeneralException, RoutingException


def configure_routes(app):

    @app.errorhandler(GeneralException)
    def exception_raised(e):
        return jsonify(e.message), e.status_code

    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify(error=str(e)), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(error=str(e)), 405

    @app.route('/api_spec', methods=['GET'])
    def api_spec():
        response = {"info": {"version": "2022.05.16"}}
        return response


    @app.route('/import', methods=['POST'])
    def import_from_google_api():
        if request.method == 'POST':
            author = request.json['author']
            imported_books = import_books_by_author(author)
            imported_books_count = 0
            if imported_books:
                    for book in imported_books:
                        if not db.session.query(exists().where(Book.external_id == book['external_id'])).scalar():
                            try:
                                new_book = Book(**book)
                                db.session.add(new_book)
                                db.session.commit()
                                imported_books_count += 1
                            except:
                                message = 'Error occured while adding book to database.'
                                raise RoutingException(message)
                        else:
                            try:
                                external_id = book['external_id']
                                book.pop('external_id')
                                db.session.query(Book).filter(Book.external_id == external_id).update(book)
                                db.session.commit()
                                imported_books_count += 1
                            except:
                                message = 'Error occured while updating book in database.'
                                raise RoutingException(message)
            response = {'imported': str(imported_books_count)}
            return response

    @app.route('/books', methods=['GET'])
    def books_get():
        if request.method == 'GET':
            try:
                args = request.args
                filters = args.to_dict()
            except:
                message = 'Error occured while accessing query string arguments.'
                raise RoutingException(message)
            filtered_books = query_string_filter(filters)
            books = []
            for book in filtered_books:
                book_details = jsonify_object(book)
                books.append(book_details)
            return jsonify(books)

    @app.route('/books/<int:_id>', methods=['GET'])
    def get_books_by_id(_id):
        if request.method == 'GET':
            book = Book.query.get(_id)
            if book:
                book_details = jsonify_object(book)
                return book_details
            else:
                response = {'info': 'This book is not in the database.'}
                return response

    @app.route('/books', methods=['POST'])
    def books_post():
        if request.method == 'POST':
            print(type(request))
            print(request)
            book_dict = request_to_dict(request)
            new_book = Book(**book_dict)
            db.session.add(new_book)
            db.session.commit()
            book_id = new_book._id
            book = Book.query.get(book_id)
            book_details = jsonify_object(book)
            return book_details

    @app.route('/books/<int:_id>', methods=['PATCH'])
    def patch_books_by_id(_id):
        if request.method == 'PATCH':
            book = Book.query.get(_id)
            updates = request.json
            db.session.query(Book).filter(Book._id == _id).update(updates)
            db.session.commit()
            book_details = jsonify_object(book)
            return book_details

    @app.route('/books/<int:_id>', methods=['DELETE'])
    def delete_books_by_id(_id):
        if request.method == 'DELETE':
            book = Book.query.get(_id)
            if book:
                db.session.delete(book)
                db.session.commit()
                response = {'info': 'Book deleted'}
            else:
                response = {'info': 'This book is not in the database.'}
            return response