
from flask import Flask, render_template, request,redirect,session,flash,make_response,jsonify,url_for
from datetime import timedelta
import requests   
import secrets
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail,Message #pip install Flask-Mail
from math import ceil
from flask_oidc import OpenIDConnect

app = Flask(__name__)

app.permanent_session_lifetime = timedelta(days=100) #if not set default is 31 days
#app.secret_key = secrets.token_hex(16)  # 32-character random key
app.secret_key = "secrete_key_here"
#sessions data are stored on the client's computer so the secrete_key would prevent users from editing the session cookie

app.config.update({
    "SECRET_KEY": "a-very-random-string-for-flask",  # not your Keycloak secret
    "OIDC_CLIENT_SECRETS": "client_secrets.json",
    "OIDC_SCOPES": ["openid", "email", "profile"],
    "OIDC_INTROSPECTION_AUTH_METHOD": "client_secret_post"
})

#Gmail
# Turn on 2-Step Verification in your Google Account.
# (Go to Google Account → Security → 2-Step Verification and enable it).
# Then go to Google Account → Security → App Passwords.
# Choose App = Mail and Device = Other (give it a name like FlaskApp).
# Google will generate a 16-character password (e.g. abcd efgh ijkl mnop).

# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = 'marusoftghana@gmail.com'
# app.config['MAIL_PASSWORD'] = 'fcda oxdb wclv aoem'
# app.config['MAIL_DEFAULT_SENDER'] = ('Maruf Ibrahim', 'marusoftghana@gmail.com')


# Email config for local debug server https://toolheap.com/test-mail-server-tool/?utm_source=chatgpt.com
app.config['MAIL_SERVER'] = 'localhost'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USERNAME'] = None
app.config['MAIL_PASSWORD'] = None
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)



def send_mail(recipient_email,recipient_name,code,user_id):
    msg_body = f"""
    <p>Hello <b>{ recipient_name }</b>,</p>

    <p>Thank you for registering at <b>DevWord Tech Academy</b>!</p>

    <p>
    To activate your account, please click the link below or copy and paste it into your browser:
    </p>

    <p>
    <a href='http://localhost:3001/account-activation?user-id={user_id}&code={code}'>{{ activation_link }}</a>
    </p>

    <p>
    <strong>Activation Code:</strong><br>http://localhost:3001/account-activation?user-id={user_id}&code={code}
    </p>

    <p>If you did not create this account, please ignore this email.</p>

    <p>Best regards,<br>
    Devworld Tech Academy Team</p>
    """
    msg = Message(
        subject="Account Activation",
        sender="info@wbta.com",
        recipients=[recipient_email],
        html=msg_body
    )
    mail.send(msg)
    


@app.before_request
def user_info():
    if 'email' in session and "lname" not in session:
        if "logout" not in request.path:
            get_user_info = requests.post("http://localhost:3000/user-info", json={"email":session["email"]})

            if get_user_info.status_code == 200:
                get_user_info = get_user_info.json()
                
                if "error" not in get_user_info:
                    session["lname"] = get_user_info["lname"]
                    session["fname"] = get_user_info["fname"]
                    session["user_id"] = get_user_info["user_id"]
                    session["prof_img"] = get_user_info["prof_img"]
                    # session["bg_img"] = get_user_info["bg_img"]
                    session["user_level"] = get_user_info["user_level"]

                else:
                   
                    return get_user_info
        #     return get_user_info
        # else:
        #     return None

        


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if "email" in session:
        return redirect("/")
    if request.method == "POST":
        # Collect form data from template
        email = request.form["email"]
        password = request.form["password"]
        lname = request.form["lname"]
        fname = request.form["fname"]
        phone = request.form["phone"]

        # Send data to backend API 
        try:
            response = requests.post(
                "http://localhost:3000/register",   
                json={
                    "email": email,
                    "password": password,
                    "lname": lname,
                    "fname": fname,
                    "phone": phone
                },
                timeout=5   # avoids hanging if backend is down
            )
           
        except:
            return "Connection to backend failed"


        if response.status_code == 201: #resource successfully created
            result = response.json()
        else:
            return response.text
        

        # Use backend JSON
        if result.get("status") == "success":

            
            recipient_name = fname + " " + lname
            send_mail(email,recipient_name,result.get('code'),result.get('user_id'))
            #return render_template("register.html", status="<p>A link has been sent to your mail.<br>Either click on the link or copy and paste the link into your address bar to activate your account</p>")
            return result.get("code")
        else:
            return render_template("register.html", status=result.get("message", "Registration failed"))
            

    # On GET just show registration form
    return render_template("register.html")


@app.route("/edit-profile",methods=["GET","POST"])
def edit_profile():
    if "email" not in session:
        return redirect("/")
    
    if request.method == "POST":
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        phone = request.form.get("phone")

        try:
            response = requests.post("http://localhost:3000/edit-profile",json={"fname":fname,"lname":lname,"phone":phone,"email":session["email"]})
        except:
            return "Connection to backend failed"
        
        if response.status_code == 200:
            if response.json().get("status") == "success":
                return redirect("/profile")
            else:
                render_template("/edit-profile")
        else:
            return response.text

    try:
        response = requests.post("http://localhost:3000/user-info",json={"email":session["email"]})
    except:
        return "Connection failed"
    if response.status_code == 200:
        user_info = response.json()
        return render_template("edit-profile.html",user_info = user_info)
    else:
        return "Internal Server Error", 500
        
        

@app.route("/log-ins", methods=["GET", "POST"])
def log_ins():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        response = requests.post(
            "http://localhost:3000/login",
            json={"email": email, "password": password}
        )

        if response.status_code == 200:
            session["email"] = email
            if 'remember' in request.form:
                session.permanent = True
                
            else:
                session.permanent = False

            # return redirect("/add-product")

            session["has_product"] = response.json()["product_id"]  
            if response.json().get("user_level") == 1:
                session["user_level_text"] = "(Admin)"
                if response.json()["product_id"] == 1:
                    return redirect("/products-admin") 
                else:
                    return redirect("/add-product") 
            elif response.json().get("user_level") == 5:
                session["user_level_text"] = "(User)"
                return redirect("/products")
            
            # if session["user_level"] == 1:
            
            # if response.json()["product_id"] == 1:
            #     return redirect("/products-admin") 
            # else:
            #     return redirect("/add-product") 
            # elif session["user_level"] == 5:
            #     return redirect("/products")
            
        else:
            return render_template("login.html", error="Invalid credentials")
    if "email" in session:
        return redirect("/")

    return render_template("login.html")












# Directory where uploaded images will be stored
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions (optional but recommended)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route("/add-product",methods=["POST","GET"])
def add_product():
    if request.method == "POST":
        form_data = request.form
        description = form_data.get("description")
        price = form_data.get("price")
        
        productName = form_data.get("productName")
        stock = form_data.get("stock")
        insert_or_update = form_data.get("button")
        
        if "productImage" in request.files:
            productImage = request.files["productImage"]
            
            if productImage.filename != "" and allowed_file(productImage.filename):
                filename = secure_filename(productImage.filename) 
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                productImage.save(filepath)
                productImage = filename
                # return f"Image uploaded successfully! <img src='/{filepath}' width='200'>"
        
            else:
                productImage = ""
                

        try:
            response = requests.post("http://localhost:3000/add-product",json={
                "description":description,
                "price":price,
                "productImage":productImage,
                "productName":productName,
                "stock":stock,
                "insert_or_update":insert_or_update
                })
        except:
            return "connection failed"

        if response.status_code == 200:
            response = response.json()
            return redirect("/products")
        else:
            return response.text
    

 
    if "email" not in session:
        return redirect("/")
    if "pid" in request.args and "action" in request.args:
        try:
            response = requests.get(f"http://localhost:3000/add-product?pid={request.args.get('pid')}&action={request.args['action']}")
        except:
            return "Connection failed"
        if response.status_code == 200:
            if response.json().get("productname"):
                response_data_dict = {
                    "productname" : response.json()["productname"],
                    "price" : response.json()["price"],
                    "stock" : response.json()["stock"],
                    "description" : response.json()["description"],
                    "img" : response.json()["img"]
                }
                return render_template("add_product.html",data=response_data_dict,pid=request.args.get("pid"))
        else:
            return response.text()
        
    return render_template("add_product.html")






@app.route('/log-outs')
def log_outs():
   
    session.clear() #destroys all sessions
    return redirect("/log-ins")
    








@app.route("/products", methods=["POST","GET"])
def products():
    
    
    try:
        page = request.args.get("page",1)
        per_page = 4

        
        response = requests.get(f"http://localhost:3000/products?page={page}&per_page={per_page}")
    except:
        return "connection failed!"
    
    

    products_dict = response.json()["products_data"]
    message = response.json().get("message")
    count_products = response.json().get("count_products")
    rows = ceil(count_products/per_page)
    
    return render_template("products.html",products = products_dict,message = message,count_products = count_products,rows=rows)
    



@app.route("/products-admin", methods=["POST","GET"])
def products_admin():
    
    if session["has_product"] == 1:
        if "pid" in request.args and "action" in request.args:
            pid = request.args["pid"]
            action = request.args.get("action")
        else:
            pid = action = None
            
        try:
            response = requests.post("http://localhost:3000/products-admin", json={"user_id":session["user_id"],"pid":pid,"action":action})
        except:
            return "connection failed!"
        
        

        products_dict = response.json()["products_data"]
        message = response.json().get("message")
        
        
        return render_template("products_admin.html",products = products_dict,message = message)
        
    else:
        return redirect ("/add-product")




@app.route("/profile")
def profile():

    try:
        response = requests.post("http://localhost:3000/user-info",json={"email":session["email"]})
    except:
        return "Coudn't connect to backend"
    
    if response.status_code == 200:
        user_info = response.json()
        return render_template("profile.html",user_info = user_info )
    else:
        return response.text
    

@app.route("/delete-img",methods=["GET"])
def delete_img():
    
    if "type" in request.args and request.args["user-id"] == str(session['user_id']):
        type = request.args.get("type")
        try:
            response = requests.get(f"http://localhost:3000/delete-img?type={type}&user_id={session['user_id']}")
            
        except:
            return "Connection failed"
        if response.status_code == 200:
            if response.json()["status"] == "success":
                if len(response.json()['file_name']) > 3:
                    if os.path.exists(f"static/uploads/{response.json()['file_name']}"):
                        os.remove(f"static/uploads/{response.json()['file_name']}")
                        
                
                return redirect("/profile")
        else:
            return response.text()
    return "Error"

@app.route("/account-activation")
def account_activation():
    user_id = request.args.get("user-id")
    code = request.args.get("code")

    try:
        response = requests.post("http://localhost:3000/account-activation", json={"user_id":user_id,"code":code})
    except:
        return "Connection to backend failed"
    
    if response.status_code == 200:
        code = response.json()["code"]
        if code == request.args.get("code"):
            try:
                response = requests.get(f"http://localhost:3000/account-activation?status=pass&user_id={user_id}")
            except:
                return "Failed to connect to the backend"
            if response.status_code == 200 and response.json().get("status") == "pass":
                return render_template("activation_pass.html")
            else:
                return "Failed to activate account"
        else:
            return  render_template("activation_failed.html")
    else:
        return "Internal Server Error"
    
@app.route("/users")
def users():
    if "email" not in session:
        return redirect("/")
    if session["user_level"] != 1:
        return redirect("/")
    try:
        page = request.args.get("page",1)
        per_page = 5
        response = requests.post(f"http://localhost:3000/user-info?page={page}&per_page={per_page}", json={"email":session["email"],"user_level":"1"})# 1 => Admin

    except:
        return "Connection to the backend failed"
    if response.status_code == 200:
        users = response.json()["users"]
        count_users = response.json()["count_users"]
        rows = ceil((count_users/per_page))
        
        return render_template("users.html", users = users,count_users=count_users,rows=rows)
    else:
        return "Internal Server Error"




oidc = OpenIDConnect(app)
from urllib.parse import quote

KEYCLOAK_BASE = "http://localhost:8080"
REALM = "master"   
CLIENT_ID = "flask-kc-id"
KEYCLOAK_LOGOUT_URL = f"{KEYCLOAK_BASE}/realms/{REALM}/protocol/openid-connect/logout"

@app.route("/keycloak")
@oidc.require_login
def keycloak():
    """Protected route showing user info."""
    user = oidc.user_getinfo(["preferred_username", "email"])
    return f"Hello, {user['preferred_username']} ({user['email']})"


@app.route("/log-in")
@oidc.require_login
def log_in():
    """Login and store ID token for logout."""
    user = oidc.user_getinfo(["sub", "preferred_username", "email"])
    
    #session["user"] = user
    session["email"] = user["email"]
    session['fname'] = user.get("given_name", "First Name")
    session['lname'] = user.get("family_name", "Last Name")
    id_token = oidc.get_access_token()
    session["id_token"] = id_token




    try:
        response = requests.post(
            "http://localhost:3000/register",   
            json={
                "email": session["email"],
                "password": "password8956874",
                "lname": session["lname"],
                "fname": session["fname"],
                "phone": "02563256",
                "src":"cloak"
            }
        )
        
    except:
        return session["email"]+session['lname']+session["fname"]
        #return "Connection to backend failed"


    if response.status_code == 201: #resource successfully created
        result = response.json()
        
    else:
        # return response.text
        return redirect("/")





   

    
    return redirect("/products")



@app.route("/log-out")
def log_out():

    session.clear()

    post_logout = url_for("logged_out", _external=True) #_external=True will give you the full path i.e http://localhost:3001/log-out
    #id_token = oidc.get_access_token()
    #add id_token to the url if you don't want to see the confirmation message when you logout. you must first save id_token when user login
    # f"?id_token_hint={id_token}"
    logout_url = (
    f"{KEYCLOAK_LOGOUT_URL}"
    f"?post_logout_redirect_uri={quote(post_logout)}"
    f"&client_id={CLIENT_ID}"
    )
  
    return redirect(logout_url)


@app.route("/logged_out")
def logged_out():
    return "✅ You have been logged out of Keycloak and Flask. <a href='/'>Go Home</a>"





if __name__ == "__main__":
    app.run(debug=True, port=3001)
