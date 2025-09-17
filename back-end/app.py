from flask import Flask, render_template, url_for,request,redirect,flash,session,make_response,jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,UTC,timezone
from flask_bcrypt import Bcrypt
import secrets
import psycopg2
import os
import requests
import random

from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow requests from frontend (3001)


app.secret_key = secrets.token_hex(16)
bcrypt = Bcrypt(app)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/ecommerce_db'
# postgresql:// → using the PostgreSQL driver
# postgres:admin → username = postgres, password = admin
# @localhost → host = localhost
# (no port specified) → so it uses default port 5432 automatically
# /ecommerce_db → database name = ecommerce_db

db = SQLAlchemy(app)

def shuffle():
    shuffle = list("abcdefghijlmnopkrstuvwxyz123456789ABCDEFGHIJKLMNOPKRSTUVWXYZ")
    random.shuffle(shuffle)
    shuffled_str = "".join(shuffle)
    return shuffled_str



class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(100), nullable=False)
    fname = db.Column(db.String(200), nullable=False)
    lname = db.Column(db.String(200), nullable=False)
    user_level = db.Column(db.SmallInteger, nullable=False, default=5) # 5=>user, 1 =>admin
    is_active = db.Column(db.Boolean,nullable=False,default=False) # True=>active, False=>inactive
    prof_img = db.Column(db.String(200),nullable=True)
    bg_img = db.Column(db.String(200),nullable=True)
    code = db.Column(db.String(300),nullable=True,default='')
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<User {self.id} - {self.email}>'


class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(200), nullable=False)  # fixed typo
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    img = db.Column(db.String(200), nullable=True)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationship
    user = db.relationship('Users', backref=db.backref('products', lazy=True))

    def __repr__(self):
        return f'<Product {self.id} - {self.productname}>'






@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()   # expecting JSON from frontend
    email = data.get("email")
    password = data.get("password")
    lname = data.get("lname")
    fname = data.get("fname")
    phone = data.get("phone")
    

    # Check if user already exists
    user = Users.query.filter_by(email=email).first()
    if user:
        return jsonify({"status": "error", "message": "User already exists"}), 400

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Create new user
    if data.get('src','not set') == 'cloak':
        new_user = Users(
            email=email,
            password=hashed_password,
            fname=fname,
            lname=lname,
            phone=phone,
            code = shuffle(),
            is_active = True,
            user_level = 5
        )
    else:
        new_user = Users(
            email=email,
            password=hashed_password,
            fname=fname,
            lname=lname,
            phone=phone,
            code = shuffle()
        )

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": "Record successfully saved","code":new_user.code,"user_id":new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Record not saved: {str(e)}"}), 500
  


   
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = Users.query.filter_by(email=email,is_active=True).first()
    product = Products.query.filter_by(user_id=user.id).first()
    if product is None:
        product_id = 0
    else:
        product_id = 1

    if user and bcrypt.check_password_hash(user.password, password):
        return jsonify({"status": "success", "message": f"Login successful","product_id":product_id,"user_level":user.user_level}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route("/add-product",methods=["POST","GET"])
def add_product():
    if request.method == "POST":

        data = request.get_json()

        description = data["description"]
        price = data["price"]
        productImage = data["productImage"]
        productName = data["productName"]
        stock = data["stock"]
        
        

        try:
            if data["insert_or_update"] == "insert":
                new_product = Products(
                productname=productName,
                price = price,
                stock = stock,
                description = description,
                img = productImage,
                user_id = 1
                )
                db.session.add(new_product)
                db.session.commit()
                return jsonify({"status":"success","message":f"Product: {productName} successfully added"})
            else:
                get_product_by_id = Products.query.get(data["insert_or_update"])
                get_product_by_id.productname=productName
                get_product_by_id.price = price
                get_product_by_id.stock = stock
                get_product_by_id.description = description
                get_product_by_id.img = productImage
                db.session.commit()
                return jsonify({"status":"success","message":f"Product: {productName} successfully updated"})
        except:
            return jsonify({"status":"error","message":"Insertion/update Failed"}), 500
    if "pid" in request.args and "action" in request.args:
        pid = request.args["pid"]
        action = request.args.get("action")
        try:
            get_product = Products.query.get(pid)
            if get_product is not None:
                product_dict = {
                    "productname": get_product.productname,
                    "price" : get_product.price,
                    "stock" : get_product.stock,
                    "description" : get_product.description,
                    "img" : get_product.img
                }
                return jsonify(product_dict)
            return jsonify({"error":"couldn't fetch product"})
        except:
            return jsonify({"error":"database connection failed"})
        
        
    
        
@app.route("/user-info",methods=["POST","GET"])
def user_info():
    if request.method == "POST":
        data = request.get_json()
        email = data.get("email")

        try:
           
            if data.get("user_level") == "1":
                count_users = Users.query.count()

                

                page = request.args.get("page",type=int())
                per_page = request.args.get("per_page",type=int())
                users = Users.query.paginate(page=page,per_page=per_page)
                users_list = []
                for user in users:
                    users_dict = {
                        "user_id":user.id,
                        "fname":user.fname,
                        "lname":user.lname,
                        "phone":user.phone,
                        "prof_img":user.prof_img,
                        "bg_img":user.bg_img,
                        "user_level":user.user_level,
                        "is_active":user.is_active
                    }
                    users_list.append(users_dict)
                return jsonify({"users":users_list,"count_users":count_users})


            user = Users.query.filter_by(email=email).first()
            return jsonify({
                "user_id":user.id,
                "fname":user.fname,
                "lname":user.lname,
                "phone":user.phone,
                "prof_img":user.prof_img,
                "user_level":user.user_level,
                "is_active":user.is_active
                })
        except:
            return jsonify({"error":"not found"})
            

@app.route("/products",methods=["GET"])
def products():
    
        
        

    page = request.args.get("page",type=int())
    per_page = request.args.get("per_page",type=int())

    products_ls = Products.query.paginate(page=page,per_page=per_page)
    # products_ls = Products.query.order_by(-Products.id).all()
    count_products = Products.query.count()

    products_data = []

    for p in products_ls:
        products_dict = {
            "product_id": p.id,
            "img" : p.img,
            "stock" : p.stock,
            "description" : p.description,
            "phone" : p.user.phone,
            "product_name": p.productname,
            "price": p.price,
            "uer_id": p.user.id,
            "fname": p.user.fname,
            "lname": p.user.lname,
            "user_level": p.user.user_level
        }
        products_data.append(products_dict)

    return jsonify({"products_data":products_data,"count_products":count_products})

@app.route("/products-admin",methods=["POST"])
def products_admin():
    data = request.get_json()
    user_id = data.get("user_id")
    pid = data["pid"]
    action = data["action"]
    message = ""
    if action == "del":
        try:
            get_product_to_delete = Products.query.get(pid)
            db.session.delete(get_product_to_delete)
            db.session.commit()
            message = f"{pid} : {get_product_to_delete.productname} successfully deleted"
        except:
            message = "Error"
        


    products_ls = Products.query.filter_by(user_id=user_id).order_by(-Products.id).all()

    products_data = []

    for p in products_ls:
        products_dict = {
            "product_id": p.id,
            "img" : p.img,
            "stock" : p.stock,
            "description" : p.description,
            "phone" : p.user.phone,
            "product_name": p.productname,
            "price": p.price,
            "uer_id": p.user.id,
            "fname": p.user.fname,
            "lname": p.user.lname,
            "user_level": p.user.user_level
        }
        products_data.append(products_dict)

    return jsonify({"products_data":products_data,"message":message})


@app.route("/edit-profile",methods=["POST"])
def edit_profile():
    data = request.get_json()
    try:
        get_user = Users.query.filter_by(email=data.get("email")).first()
        get_user.lname = data.get("lname")
        get_user.fname = data.get("fname")
        get_user.phone = data.get("phone")
        db.session.commit()
        return jsonify({"status":"success","message":"Record Successfully Updated"})
    except:
        return jsonify({"status":"failed","message":"Record Not Updated"})


@app.route("/delete-img")
def delete_img():
    data = request.args
    user_id = data.get("user_id")
    try:
        get_user = Users.query.get(user_id)
    except:
        return jsonify({"error":"connection to database failed"})
    if data.get("type") == "prof":
        file_name = get_user.prof_img
        get_user.prof_img = ""
        db.session.commit()
    else:
        file_name = get_user.bg_img
        get_user.bg_img = ""
        db.session.commit()
        
    return jsonify({"status":"success","file_name":file_name})

    
@app.route("/account-activation", methods=["POST","GET"])
def account_activation():
    if request.method == "POST":
        user_id = request.get_json()["user_id"]
        code = request.get_json().get("code")
        get_user = Users.query.get(user_id)
        return jsonify({"code":get_user.code})
    if "user_id" in request.args:
        get_user =  Users.query.get(request.args.get("user_id"))
        get_user.is_active = True
        db.session.commit()
        return jsonify({"status":"pass"})

if __name__ == "__main__":
    with app.app_context():
        #db.drop_all() #drop all tables
        db.create_all()
    app.run(debug=True, port=3000, host="0.0.0.0")