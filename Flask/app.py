from flask import Flask, render_template, request, session
import cv2
import pickle
import cvzone
import numpy as np
import ibm_db
import re

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'

conn = ibm_db.connect("DATABASE=bludb;HOSTNAME=6667d8e9-9d4d-4ccb-ba32-21da3bb5aafc.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud;PORT=30376;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=ygp12091;PWD=wSRIy6tQ43AhkJ0a", "", "")
if conn:
    print("Connected")

@app.route("/")
def project():
    return render_template("home.html")

@app.route("/sign_up", methods = ['GET','POST'])
def signup():
    if request.method == 'GET':
        return render_template('sign.html')
    elif request.method == 'POST':
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        sql = "SELECT * FROM REGISTER WHERE name = ?"
        stmt = ibm_db.prepare(conn,sql)
        ibm_db.bind_param(stmt, 1, name)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        print(account)
        if account:
            return render_template('login.html', error = True)
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = "Invalid Email Address!"
            return render_template('sign.html', msg = msg)
        else:
            insert_sql = "INSERT INTO REGISTER VALUES (?,?,?)"
            prep_stmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(prep_stmt, 1, name)
            ibm_db.bind_param(prep_stmt, 2, email)
            ibm_db.bind_param(prep_stmt, 3, password)
            ibm_db.execute(prep_stmt)
            msg = "You have successfully registered !"
            return render_template('login.html', msg=msg)        
    
@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]
        sql = "SELECT * FROM REGISTER WHERE EMAIL=? AND PASSWORD=?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt, 1, email)
        ibm_db.bind_param(stmt, 2, password)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        print(account)
        if account:
            session['Loggedin'] = True
            session['id'] = account['EMAIL']
            session['email'] = account['EMAIL']
            return render_template('model.html')
        else:
            msg = "Incorrect Email/password"
            return render_template("login.html", msg=msg)
    else:
        return render_template("login.html")

@app.route('/predict_live')
def liv_pred():
    # Video feed
    cap = cv2.VideoCapture('carParkingInput.mp4')

    if not cap.isOpened():
        print("Error: could not open video.")


    # Loading the ROI from parkingSlotPosition file
    with open('parkingSlotPosition', 'rb') as f:
        posList = pickle.load(f)
    print(len(posList))
    #Define width and height
    width, height = 107, 48

    def checkParkingSpace(imgpro):
        spaceCounter = 0
        for pos in posList:
            x, y = pos

            # Crop the image  based on ROI
            imgcrop = imgpro[y:y + height, x:x + width]

            # Counting the pixel values from cropped image
            count = cv2.countNonZero(imgcrop)

            if count<900:
                color = (0, 255, 0)
                thickness = 5
                spaceCounter += 1
            else:
                color = (0, 0, 255)
                thickness = 2

            # Draw the rectangle based on the condition defined above
            cv2.rectangle(img, pos, (pos[0] + width, pos[1] + height), color, thickness) 
        
        # Display the available parking slot count / total parking slot count
        cvzone.putTextRect(img, f'Free: {spaceCounter}/{len(posList)}', (100, 50), scale=3, thickness=5, offset=20, colorR=(0, 200, 0))
    while True:
        # Looping the video
        if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Reading frame by frame from video
        success, img = cap.read()
        
        # Converting to gray scale image
        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1) # Applying blur to image

        # Applying threshold to image
        imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
        imgMedian = cv2.medianBlur(imgThreshold, 5) # Applying blur to image

        kernel = np.ones((3, 3), np.uint8)
        imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)

        # Passing dilate image to the function
        checkParkingSpace(imgDilate)
        cv2.imshow("Image", img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    return render_template('model.html')

if __name__ == "__main__":
    app.run(debug=True)