from functools import wraps
from flask import Flask, jsonify, request, make_response
from flask_jwt import jwt_required, current_identity
from flask_restful import Resource, Api, abort
from datetime import datetime, timedelta
import sqlite3 as sql
import re
import sys
import hashlib
import psycopg2
from psycopg2.extras import DictCursor
from bloodedguild_forums_api.clean_html import clean_html
from bloodedguild_forums_api.db import (
    DatabaseAuth,
    DatabaseConnector,
    DatabaseStringConstructor
)
testing = False
if(not testing):
    from bloodedguild_forums_api.config import config
else:
    from bloodedguild_forums_api.testing_config import config

GROUP_ADMINISTRATORS = ["gm", "dev"]
app = Flask(__name__)
api = Api(app)

def get_post_count(thread_id):
    db = DatabaseConnector()
    psql_cursor = db.get_cursor()
    sql_string = "select COUNT(*) from posts "
    sql_string += "where thread_id = %s;"
    psql_cursor.execute(
        sql_string,
        (thread_id,)
    )
    post_count = psql_cursor.fetchone()[0]
    psql_cursor.close()
    db.close()
    return post_count

class ValidatorResource(Resource):
    def __init__(self, required_fields=[]):
        super().__init__()
        self.required_fields = required_fields

    def validate_json(self, json_data):
        missing_fields = []
        for field in self.required_fields:
            if(field not in json_data.keys()):
                missing_fields.append(field)
        if(missing_fields):
            error_string = "The JSON data was missing the following fields:"
            for field in missing_fields:
                error_string += field+","
                error_string = error_string[:-1] #trim last comma
                abort(400, message=error_string)
        else:
            return json_data

class DefaultLocation(Resource):
    def get(self):
        return {'info': 'Bloodedguild forums api. Do not touch! wow!'}


class ForumsUser(Resource):
    def get(self, user_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select U.id, U.f_name, U.l_name, U.username, U.email, "
        sql_string += "U.avatar, U.signature, U.count, U.name from "
        sql_string += "users_post_counts as U "
        sql_string += "where U.id = %s;"
        psql_cursor.execute(
            sql_string,
            (user_id,)
        )
        user = psql_cursor.fetchone()
        if(not user):
            user = []
        else:
            user_object = {
                'type': 'user',
                'id': user[0],
                'f_name': user[1],
                'l_name': user[2],
                'username': user[3],
                'email': user[4],
                'avatar': user[5],
                'signature': user[6],
                'post_count': user[7],
                'group': user[8]
            }
            user = [user_object]
        psql_cursor.close()
        db.close()
        return user

class ForumsModifyUser(Resource):
    method_decorators = [jwt_required()]
    def validate_json(self, json_data):
        if(not json_data):
            abort(400, message="JSON data was empty.")
        possible_fields = ["password_hash", "avatar", "signature"]
        bad_fields = []
        for field in json_data.keys():
            if(field not in possible_fields):
                bad_fields.append(field)
        if(bad_fields):
            error_string = "The JSON data had the following bad fields:"
            for field in missing_fields:
                error_string += field+","
                error_string = error_string[:-1] #trim last comma
                abort(400, message=error_string)
        else:
            return json_data

    def run_sql_query(self, json_data):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        json_keys = list(json_data.keys())
        sql_arguments = []
        sql_string = "update users set ("
        sql_string += json_keys[0] + ") = ("
        if("password_hash" in json_keys):
            sql_string += "crypt(%s, gen_salt('bf', 8))) where "
            sql_arguments.append(json_data["password_hash"])
        elif("avatar" in json_keys):
            sql_string += "%s) where "
            sql_arguments.append(json_data["avatar"])
        else:
            sql_string += "%s) where "
            sql_arguments.append(json_data["signature"])
        sql_string += "id = %s;"
        sql_arguments.append(current_identity.id)
        try:
            psql_cursor.execute(
                sql_string,
                tuple(sql_arguments)
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        psql_cursor.close()
        db.close()

    def validate_avatar_link(self, link):
        allowed_sites = ["i.imgur.com"]
        from_allowed_site = False
        for site in allowed_sites:
            if(site in link):
                from_allowed_site = True
                break
        if(not from_allowed_site):
            abort(400, message="Error: avatar link was from bad site.")
            regex = re.compile(r'^http[s]?:\\/\\/')
        subbed_link = re.sub(r'^http[s]?:\/\/', '', link)
        return subbed_link

    def patch(self):
        json_data = self.validate_json(request.get_json())
        response = {}
        if('avatar' in json_data):
            json_data['avatar'] = self.validate_avatar_link(
                json_data['avatar']
            )
            response['avatar'] = json_data['avatar']
        if('signature' in json_data):
            json_data['signature'] = clean_html(json_data['signature'])
        self.run_sql_query(json_data)
        response['type'] = 'user'
        response['status'] = 'updated'
        return response

class ForumsAddUser(ValidatorResource):
    def validate_user_name(self, user_name):
        regex_user_name = re.compile(r'^[0-9a-zA-Z_]+$')
        if(len(user_name) > 30):
            abort(
                400,
                message="Error: Username was longer than 30 characters."
            )
        if(not regex_user_name.match(user_name)):
            abort(400, message="Error: Username had bad characters.")

    def put(self):
        json_data = self.validate_json(request.get_json())
        self.validate_user_name(json_data['username'])
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "insert into users "
        sql_string += "(f_name, "
        sql_string += "l_name, "
        sql_string += "username, "
        sql_string += "password_hash, "
        sql_string += "email, "
        sql_string += "group_id) "
        sql_string += "VALUES("
        sql_string += "%s, "
        sql_string += "%s, "
        sql_string += "%s, "
        sql_string += "crypt(%s, gen_salt('bf', 8)), "
        sql_string += "%s, "
        sql_string += "1) returning id;"
        try:
            psql_cursor.execute(
                sql_string,
                (
                    json_data['f_name'],
                    json_data['l_name'],
                    json_data['username'],
                    json_data['password_hash'],
                    json_data['email']
                )
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        new_id = psql_cursor.fetchone()[0]
        psql_cursor.close()
        db.close()
        return {
            'type': 'user',
            'username': json_data["username"],
            'id': new_id,
            'status': 'created'
        }


class ForumsCategoriesInfo(Resource):
    def construct_subquery_response(self, sql_query):
        post_response = {}
        if(sql_query[5]):
            user = {
                'type': 'user',
                'id': sql_query[8],
                'username': sql_query[10],
                'avatar': sql_query[11],
                'group': sql_query[12]
            }
            post_response = {
                'type': 'post',
                'id': sql_query[5],
                'thread_id': sql_query[6],
                'title': sql_query[7],
                'timestamp': sql_query[9].isoformat(),
                'user': user
            }
        return {
            'type': 'subcategory',
            'id': sql_query[0],
            'title': sql_query[1],
            'description': sql_query[2],
            'thread_count': int(sql_query[4]),
            'post': post_response
        }

    def construct_response(self, sql_query):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from subcategories_thread_counts "
        sql_string += "LEFT JOIN subcategories_main on "
        sql_string += "(subcategories_thread_counts.id = subcategories_main.id) "
        sql_string += "where category_id = %s "
        sql_string += "order by subcategories_thread_counts.id asc;"
        psql_cursor.execute(
            sql_string,
            (sql_query[0],)
        )
        forum_subcategories = psql_cursor.fetchall()
        forum_subcategories = [
            self.construct_subquery_response(subcategory)
            for subcategory in
            forum_subcategories
        ]
        psql_cursor.close()
        db.close()
        return {
                'type': 'category',
                'id': sql_query[0],
                'title': sql_query[1],
                'description': sql_query[2],
                'subcategories': forum_subcategories
        }

    def get(self):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select * from categories;"
        psql_cursor.execute(
            sql_string
        )
        forum_categories = psql_cursor.fetchall()
        psql_cursor.close()
        db.close()
        response = []
        if(forum_categories):
            response = [
                self.construct_response(category)
                for category in
                forum_categories
            ]
        return response


class ForumsSubcategoriesInfo(Resource):
    def get(self, category_id):
        return {'type': 'category'}


class ForumsSubcategoryInfo(Resource):
    def construct_response(self, sql_query):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select COUNT(*) from "
        sql_string += "threads "
        sql_string += "WHERE subcategory_id = %s;"
        psql_cursor.execute(
            sql_string,
            (sql_query[0],)
        )
        thread_count = psql_cursor.fetchone()[0]
        psql_cursor.close()
        db.close()
        category = {
            'type': 'category',
            'id': sql_query[4],
            'title': sql_query[5]
        }
        return {
            'type': 'subcategory',
            'id': sql_query[0],
            'title': sql_query[1],
            'description': sql_query[2],
            'thread_count': thread_count,
            'category': category
        }

    def get(self, subcategory_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select *, categories.id, categories.title "
        sql_string += "from subcategories, categories "
        sql_string += "where subcategories.id = %s AND "
        sql_string += "categories.id = subcategories.category_id;"
        psql_cursor.execute(
            sql_string,
            (subcategory_id,)
        )
        forum_subcategory = psql_cursor.fetchone()
        return self.construct_response(forum_subcategory)


class ForumsSubcategoryThreads(Resource):
    def construct_response(self, sql_query):
        user_thread = {
            'type': 'user',
            'id': sql_query[5],
            'username': sql_query[6],
            'group': sql_query[12]
        }
        user_post = {
            'type': 'user',
            'id': sql_query[8],
            'username': sql_query[9],
            'avatar': sql_query[10],
            'group': sql_query[11]
        }
        return {
            'type': 'thread',
            'id': sql_query[0],
            'title': sql_query[1],
            'timestamp': sql_query[2].isoformat(),
            'locked': sql_query[3],
            'sticky': sql_query[4],
            'user_thread': user_thread,
            'user_post': user_post,
            'post_count': get_post_count(sql_query[0]),
            'posts_timestamp': sql_query[7].isoformat(),
        }

    def get_thread(self, subcategory_id, thread_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        offset = int(thread_id)-1 #0 indexed
        sql_string = "select threads.id, threads.title, threads.timestamp, "
        sql_string += "threads.locked, threads.sticky, threads.user_id, "
        sql_string += "t_users.username, posts.timestamp, "
        sql_string += "posts.user_id, p_users.username , p_users.avatar, "
        sql_string += "g_posts.name, g_threads.name "
        sql_string += "from threads, posts, "
        sql_string += "users as t_users, users as p_users, "
        sql_string += "groups as g_threads, groups as g_posts where "
        sql_string += "threads.subcategory_id = %s and "
        sql_string += "threads.id = posts.thread_id and "
        sql_string += "posts.id = ("
        sql_string += "select max (id) from posts where "
        sql_string += "posts.thread_id = threads.id) "
        sql_string += "and t_users.id = threads.user_id and "
        sql_string += "p_users.id = posts.user_id and "
        sql_string += "g_posts.id = p_users.group_id and "
        sql_string += "g_threads.id = t_users.group_id "
        sql_string += "order by threads.sticky desc, posts.timestamp desc "
        sql_string += "limit 1 "
        sql_string += "offset %s;"
        psql_cursor.execute(
            sql_string,
            (subcategory_id, offset)
        )
        forum_post = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        if(not forum_post):
            forum_post = []
        else:
            forum_post = [self.construct_response(forum_post)]
        return forum_post

    def get_threads(self, subcategory_id, thread_min, thread_max):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select threads.id, threads.title, threads.timestamp, "
        sql_string += "threads.locked, threads.sticky, threads.user_id, "
        sql_string += "t_users.username, posts.timestamp, "
        sql_string += "posts.user_id, p_users.username , p_users.avatar, "
        sql_string += "g_posts.name, g_threads.name "
        sql_string += "from threads, posts, "
        sql_string += "users as t_users, users as p_users, "
        sql_string += "groups as g_threads, groups as g_posts where "
        sql_string += "threads.subcategory_id = %s and "
        sql_string += "threads.id = posts.thread_id and "
        sql_string += "posts.id = ("
        sql_string += "select max (id) from posts where "
        sql_string += "posts.thread_id = threads.id) "
        sql_string += "and t_users.id = threads.user_id and "
        sql_string += "p_users.id = posts.user_id and "
        sql_string += "g_posts.id = p_users.group_id and "
        sql_string += "g_threads.id = t_users.group_id "
        sql_string += "order by threads.sticky desc, posts.timestamp desc "
        sql_string += "limit %s "
        sql_string += "offset %s;"
        limit = (thread_max - thread_min) + 1
        offset = thread_min-1 #0 indexed
        psql_cursor.execute(
            sql_string,
            (
                subcategory_id,
                limit,
                offset
            )
        )
        forum_threads = psql_cursor.fetchall()
        psql_cursor.close()
        db.close()
        return [self.construct_response(thread) for thread in forum_threads]

    def get(self, subcategory_id, thread_id):
        regex_post = re.compile(r'^\d+$')
        regex_posts = re.compile(r'^(?P<min>\d+)-(?P<max>\d+)$')
        response = {}
        if(regex_post.match(thread_id)):
            response = self.get_thread(
                subcategory_id,
                thread_id
            )
        elif(regex_posts.match(thread_id)):
            matches = regex_posts.match(thread_id)
            min = int(matches.group('min'))
            max = int(matches.group('max'))
            if(min < max and min != 0):
                response = self.get_threads(
                    subcategory_id,
                    min,
                    max
                )
            else:
                error_message = "Minimum ID given was larger than Maximum ID."
                abort(400, message="Error:"+error_message)
        else:
            abort(400, message="Error: thread id did not match regex")
        return response


class ForumsInfo(Resource):
    def get(self):
        return {
            'type': 'forums',
        }


class ForumsAddThread(ValidatorResource):
    method_decorators = [jwt_required()]
    def put(self, subcategory_id):
        json_data = self.validate_json(request.get_json())
        if(not json_data["title"]):
            abort(401, message="Error: Title is blank.")
        db = DatabaseConnector()
        sql_string = "insert into threads "
        sql_string += "("
        sql_string += "title, "
        sql_string += "subcategory_id, "
        sql_string += "user_id"
        sql_string += ") "
        sql_string += "VALUES (%s, %s, %s) RETURNING id;"
        psql_cursor = db.get_cursor()
        try:
            psql_cursor.execute(
                sql_string,
                (
                    json_data["title"],
                    subcategory_id,
                    current_identity.id
                )
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        new_id = psql_cursor.fetchone()[0]
        sql_string = "insert into posts "
        sql_string += "("
        sql_string += "content, "
        sql_string += "thread_id, "
        sql_string += "user_id"
        sql_string += ") "
        sql_string += "VALUES (%s, %s, %s) RETURNING id;"
        try:
            psql_cursor.execute(
                sql_string,
                (
                    clean_html(json_data["content"]),
                    new_id,
                    current_identity.id
                )
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        psql_cursor.close()
        db.close()
        return {
            'type': 'thread',
            'title': json_data["title"],
            'id': new_id,
            'status': 'created'
        }


class ForumsModifyThread(Resource):
    method_decorators = [jwt_required()]
    def validate_json(self, json_data):
        if(not json_data):
            abort(400, message="JSON data was empty.")
        possible_fields = ["locked", "sticky"]
        bad_fields = []
        for field in json_data.keys():
            if(field not in possible_fields):
                bad_fields.append(field)
        if(bad_fields):
            error_string = "The JSON data had the following bad fields:"
            for field in missing_fields:
                error_string += field+","
                error_string = error_string[:-1] #trim last comma
                abort(400, message=error_string)
        else:
            return json_data

    def patch(self, thread_id):
        json_data = self.validate_json(request.get_json())
        if(current_identity.group not in GROUP_ADMINISTRATORS):
            abort(
                403,
                message="Error: This is for administrators only."
            )
        db = DatabaseConnector()
        json_key = list(json_data.keys())[0]
        json_value = json_data[json_key]
        sql_string = "update threads set ("+ json_key + ") = (%s) where "
        sql_string += "threads.id = %s;"
        psql_cursor = db.get_cursor()
        try:
            psql_cursor.execute(
                sql_string,
                (json_value, thread_id)
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        psql_cursor.close()
        db.close()
        return {
            "type": "thread",
            "id": thread_id,
            json_key: json_value,
            "status": "updated"
        }

    def delete(self, thread_id):
        if(current_identity.group not in GROUP_ADMINISTRATORS):
            abort(
                403,
                message="Error: This is for administrators only."
            )
        db = DatabaseConnector()
        sql_string = "delete from threads where "
        sql_string += "id = %s;"
        psql_cursor = db.get_cursor()
        try:
            psql_cursor.execute(
                sql_string,
                (thread_id,)
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        psql_cursor.close()
        db.close()
        return {
            "type": "thread",
            "id": thread_id,
            "status": "deleted"
        }



class ForumsThread(ValidatorResource):
    def construct_response(self, sql_query):
        user = {
            'type': 'user',
            'id': sql_query[5],
            'username': sql_query[6],
            'group': sql_query[7]
        }
        subcategory = {
            'type': 'subcategory',
            'id': sql_query[8],
            'title': sql_query[9]
        }
        category = {
            'type': 'category',
            'id': sql_query[10],
            'title': sql_query[11]
        }
        return {
            'type': 'thread',
            'id': sql_query[0],
            'title': sql_query[1],
            'timestamp': sql_query[2].isoformat(),
            'locked': sql_query[3],
            'sticky': sql_query[4],
            'post_count': get_post_count(sql_query[0]),
            'user': user,
            'subcategory': subcategory,
            'category': category
        }

    def get(self, thread_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select threads.id, threads.title, threads.timestamp, "
        sql_string += "threads.locked, threads.sticky, "
        sql_string += "users_post_counts.id, users_post_counts.username, "
        sql_string += "users_post_counts.name, "
        sql_string += "subcategories.id, subcategories.title, "
        sql_string += "categories.id, categories.title FROM "
        sql_string += "threads, users_post_counts, "
        sql_string += "subcategories, categories "
        sql_string += "where threads.id = %s and "
        sql_string += "users_post_counts.id = threads.user_id and "
        sql_string += "subcategories.id = threads.subcategory_id and "
        sql_string += "categories.id = subcategories.category_id;"
        psql_cursor.execute(
            sql_string,
            (thread_id,)
        )
        forum_thread = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        response = []
        if(forum_thread):
            response = [self.construct_response(forum_thread)]
        return response


class ForumsAddPost(ValidatorResource):
    method_decorators = [jwt_required()]
    def put(self, thread_id):
        json_data = self.validate_json(request.get_json())
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        new_post_id = get_post_count(thread_id) + 1
        sql_string = "insert into posts "
        sql_string += "("
        sql_string += "content, "
        sql_string += "thread_id, "
        sql_string += "user_id"
        sql_string += ") "
        sql_string += "VALUES (%s, %s, %s) RETURNING "
        sql_string += "(select locked from "
        sql_string += "threads where threads.id = %s);"
        try:
            psql_cursor.execute(
                sql_string,
                (
                    clean_html(json_data["content"]),
                    thread_id,
                    current_identity.id,
                    thread_id
                )
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        locked = psql_cursor.fetchone()[0]
        psql_cursor.close()
        if(locked):
            db.rollback()
            abort(400, message="Error: Thread given was locked.")
        db.close()
        return {
            'thread': thread_id,
            'type': 'post',
            'status': 'created',
            'post_id': new_post_id
        }

class ForumsLatestPosts(Resource):
    def construct_response(self, sql_query):
        user = {
            'type': 'user',
            'id': sql_query[3],
            'username': sql_query[4],
            'avatar': sql_query[5],
            'group': sql_query[6]
        }
        thread = {
            'type': 'thread',
            'id': sql_query[7],
            'title': sql_query[8]
        }
        return {
            'type': 'post',
            'id': sql_query[0],
            'content': sql_query[1],
            'timestamp': sql_query[2].isoformat(),
            'user': user,
            'thread': thread
        }

    def get(self, amount):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select P.id, P.content, P.timestamp, "
        sql_string += "U.id, U.username, U.avatar, U.name, "
        sql_string += "T.id, T.title "
        sql_string += "from posts as P, users_post_counts as U, "
        sql_string += "threads as T "
        sql_string += "where P.thread_id = T.id and "
        sql_string += "U.id = P.user_id "
        sql_string += "order by P.id desc "
        sql_string += "limit %s; "
        psql_cursor.execute(
            sql_string,
            (amount,)
        )
        forum_posts = psql_cursor.fetchall()
        forum_posts = [self.construct_response(post) for post in forum_posts]
        psql_cursor.close()
        db.close()
        return forum_posts


class ForumsPost(Resource):
    def construct_response(self, sql_query):
        user = {
            'type': 'user',
            'id': sql_query[4],
            'username': sql_query[5],
            'avatar': sql_query[6],
            'post_count': sql_query[7],
            'group': sql_query[8],
            'signature': sql_query[9]
        }
        return {
            'type': 'post',
            'id': sql_query[0],
            'content': sql_query[1],
            'timestamp': sql_query[2].isoformat(),
            'edited_timestamp': sql_query[3].isoformat(),
            'user': user
        }

    def get_post(self, thread_id, post_id):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        offset = int(post_id)-1 #offset is 0 indexed
        sql_string = "select P.id, P.content, P.timestamp, "
        sql_string += "P.edited_timestamp, U.id, U.username, U.avatar, "
        sql_string += "U.count, U.name, U.signature "
        sql_string += "from posts as P, users_post_counts as U "
        sql_string += "where P.thread_id = %s and "
        sql_string += "U.id = P.user_id "
        sql_string += "order by P.id "
        sql_string += "limit 1 "
        sql_string += "offset %s;"
        psql_cursor.execute(
            sql_string,
            (thread_id, offset)
        )
        forum_post = psql_cursor.fetchone()
        psql_cursor.close()
        db.close()
        if(not forum_post):
            forum_post = []
        else:
            forum_post = [self.construct_response(forum_post)]
        return forum_post

    def get_posts(self, thread_id, post_min, post_max):
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select P.id, P.content, P.timestamp, "
        sql_string += "P.edited_timestamp, U.id, U.username, U.avatar, "
        sql_string += "U.count, U.name, U.signature "
        sql_string += "from posts as P, users_post_counts as U "
        sql_string += "where P.thread_id = %s and "
        sql_string += "U.id = P.user_id "
        sql_string += "order by P.id "
        sql_string += "limit %s "
        sql_string += "offset %s;"
        limit = (post_max - post_min) + 1
        offset = post_min - 1
        psql_cursor.execute(
            sql_string,
            (
                thread_id,
                limit,
                offset
            )
        )
        forum_posts = psql_cursor.fetchall()
        psql_cursor.close()
        db.close()
        return [self.construct_response(post) for post in forum_posts]

    def get(self, thread_id, post_id):
        regex_post = re.compile(r'^\d+$')
        regex_posts = re.compile(r'^(?P<min>\d+)-(?P<max>\d+)$')
        response = {}
        if(regex_post.match(post_id)):
            response = self.get_post(thread_id, post_id)
        elif(regex_posts.match(post_id)):
            matches = regex_posts.match(post_id)
            min = int(matches.group('min'))
            max = int(matches.group('max'))
            if(min < max):
                response = self.get_posts(
                    thread_id,
                    min,
                    max
                )
            else:
                error_message = "Minimum ID given was larger than Maximum ID."
                abort(400, message="Error: "+error_message)
        else:
            abort(400, message="Error: post id did not match regex")
        return response

class ForumsModifyPost(ValidatorResource):
    method_decorators = [jwt_required()]
    def patch(self, thread_id, post_id):
        json_data = self.validate_json(request.get_json())
        offset = int(post_id)-1 #0 indexed
        db = DatabaseConnector()
        psql_cursor = db.get_cursor()
        sql_string = "select posts.id, posts.user_id from posts "
        sql_string += "where posts.thread_id = %s "
        sql_string += "order by posts.timestamp asc "
        sql_string += "limit 1 "
        sql_string += "offset %s;"
        psql_cursor.execute(
            sql_string,
            (thread_id, offset)
        )
        post = psql_cursor.fetchone()
        if(not post):
            abort(
                404,
                message="Error: post did not exist"
            )
        true_post_id = post[0]
        user_id = post[1]
        if(current_identity.id != user_id):
            abort(
                400,
                message="Error: user logged in did not make this post"
            )
        sql_string = "update posts set (content, edited_timestamp) = "
        sql_string += "(%s, "
        sql_string += "now() at time zone 'utc') where "
        sql_string += "posts.id = %s returning "
        sql_string += "(select locked from threads "
        sql_string += "where threads.id = posts.thread_id)"
        try:
            psql_cursor.execute(
                sql_string,
                (
                    clean_html(json_data["content"]),
                    true_post_id
                )
            )
        except psycopg2.IntegrityError:
            abort(400, message="Error: Database failed to execute insert.")
        locked = psql_cursor.fetchone()[0]
        psql_cursor.close()
        if(locked):
            db.rollback()
            abort(400, message="Error: Thread was locked.")
        db.close()
        return {
            "type": "post",
            "id" : true_post_id,
            "status": "updated"
        }

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add(
        'Access-Control-Allow-Headers',
        'Content-Type, Authorization, Fresh-Token'
    )
    response.headers.add(
        'Access-Control-Allow-Methods',
        'GET,PUT,POST,DELETE,PATCH'
    )
    return response

api.add_resource(DefaultLocation, '/')
threads_required_fields = ([["title", "content"]])
posts_required_fields = ([["content"]])
users_required_fields = ([[
    "f_name",
    "l_name",
    "username",
    "password_hash",
    "email"
]])
posts_required_fields = ([[
    "content"
]])
api.add_resource(
    ForumsCategoriesInfo,
    '/forums/categories'
)
api.add_resource(
    ForumsSubcategoriesInfo,
    '/forums/categories/<int:category_id>'
)
api.add_resource(
    ForumsSubcategoryInfo,
    '/forums/subcategories/<int:subcategory_id>'
)
api.add_resource(
    ForumsSubcategoryThreads,
    '/forums/subcategories/<int:subcategory_id>/<string:thread_id>'
)
api.add_resource(
    ForumsModifyThread,
    '/forums/threads/<int:thread_id>',
)
api.add_resource(
    ForumsAddThread,
    '/forums/subcategories/<int:subcategory_id>',
    resource_class_args=threads_required_fields
)
api.add_resource(ForumsInfo,'/forums')
api.add_resource(ForumsThread, '/forums/threads/<int:thread_id>')
api.add_resource(
    ForumsAddPost,
    '/forums/threads/<int:thread_id>',
    resource_class_args=posts_required_fields
)
api.add_resource(
    ForumsModifyPost,
    '/forums/threads/<int:thread_id>/<int:post_id>',
    resource_class_args=posts_required_fields
)
api.add_resource(
    ForumsPost,
    '/forums/threads/<int:thread_id>/<string:post_id>',
)
api.add_resource(
    ForumsUser,
    '/forums/users/<int:user_id>'
)
api.add_resource(
    ForumsAddUser,
    '/forums/users',
    resource_class_args=users_required_fields
)
api.add_resource(
    ForumsModifyUser,
    '/forums/users'
)
api.add_resource(
    ForumsLatestPosts,
    '/forums/posts/<int:amount>'
)
if __name__ == '__main__':
    app.run(debug=True)
