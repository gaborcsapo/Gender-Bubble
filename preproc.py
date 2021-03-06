import sys, os
sys.path.append(os.path.abspath("/home/gc1569/Capstone/Landmark_Detection/dlib/python_examples"))
sys.path.append(os.path.abspath("/home/gc1569/Image_collector/face_classification/src/utils"))
sys.path.append(os.path.abspath("/home/gc1569/Image_collector/face_classification/src"))

import math
import numpy as np
from PIL import Image
from os import listdir
from skimage import io
import matplotlib.pyplot as plt
from inference import draw_text
from datasets import get_labels
from os.path import isfile, join
from inference import load_image
from inference import detect_faces
from keras.models import load_model
from inference import apply_offsets
from inference import draw_bounding_box
from preprocessor import preprocess_input
from inference import load_detection_model
from utils import extract_left_eye_center, extract_right_eye_center, get_rotation_matrix, crop_image 
import importlib, cv2, json, os.path, random, glob, multiprocessing, argparse, fcntl, imghdr, dlib, re
    
#aligner constants
scale = 1
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("/home/gc1569/Image_collector/face_classification/"\
                                     "src/shape_predictor_68_face_landmarks.dat")
#gender prediction constants
detection_model_path = '/home/gc1569/Image_collector/face_classification'\
'/trained_models/detection_models/haarcascade_frontalface_default.xml'
emotion_model_path = '/home/gc1569/Image_collector/face_classification'\
'/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5'
gender_model_path = '/home/gc1569/Image_collector/face_classification'\
'/trained_models/gender_models/simple_CNN.81-0.96.hdf5'
emotion_labels = get_labels('fer2013')
gender_labels = get_labels('imdb')
#loading models
face_detection = load_detection_model(detection_model_path)
gender_classifier = load_model(gender_model_path, compile=False)
#getting input model shapes for inference
gender_target_size = gender_classifier.input_shape[1:3]
#hyper-parameters for bounding boxes shape
gender_offsets = (30, 60)
gender_offsets = (10, 10)


#crops images to face (in seperate iamges if more faces) and output the landmark features in a text file
def align_face(name):
    input_image, output_image = source+name, destination+name    

    #reading image. If 0 bytes we delete it
    output = input_image + ''
    img = cv2.imread(input_image)
    if img is None:
        if(os.path.isfile(input_image)):
            os.remove(input_image)
        return 'fail'
    
    #scaling images
    height, width = img.shape[:2]
    if (width == 0 or height == 0):
        no_removes += 1
        os.remove(input_image)
        return 'fail'
    s_height, s_width = height // scale, width // scale
    img = cv2.resize(img, (s_width, s_height))
    output += ' | ' + str(s_width) + ' | ' + str(s_height)
    
    #detects faces. If no faces -> remove
    dets = detector(img, 1)
    output += ' | ' + str(len(dets)) + '\n'
    if (len(dets) == 0):
        os.remove(input_image)
        return 'fail'
    
    #looping through each face, rotating it, cropping, saving, then reading in again and outputting the landmark points
    for i, det in enumerate(dets):
        shape = predictor(img, det)
        #rotate eyes to horizontal
        left_eye = extract_left_eye_center(shape)
        right_eye = extract_right_eye_center(shape)
        output += 'eyes: '+str(left_eye) + ' ' + str(right_eye)+' | '
        M = get_rotation_matrix(left_eye, right_eye)
        rotated = cv2.warpAffine(img, M, (s_width, s_height), flags=cv2.INTER_CUBIC)
        
        cropped = crop_image(rotated, det)
        if (cropped.shape[1] == 0):
            continue
        #saving    
        if output_image.endswith('.jpg'):
            output_image_path = output_image.replace('.jpg', '_%i.jpg' % i)
        elif output_image.endswith('.png'):
            output_image_path = output_image.replace('.png', '_%i.jpg' % i)
        else:
            output_image_path = output_image + ('_%i.jpg' % i)
        output += ' | ' + output_image_path + ' | ' + str(cropped.shape)
        cv2.imwrite(output_image_path, cropped)
    
        #landmark detection
        try:
            LM_img = io.imread(output_image_path)
        except:
            os.remove(output_image_path)
            return
        dets = detector(LM_img, 1)
        output += ("Number of faces detected: {}".format(len(dets)))
        if (len(dets) == 0):
            os.remove(output_image_path)
            
        for k, d in enumerate(dets):
            output += (" | Detection {}: Left: {} Top: {} Ri: {} Bot: {}".format(k, d.left(), d.top(), d.right(), d.bottom()))
            shape = predictor(LM_img, d)
            with open(output_image_path + '.txt', 'w') as lm:
                for i in range(shape.num_parts):
                    lm.write(str(shape.part(i).x) + ' ' + str(shape.part(i).y) + '\n')
    
    #print(output + '\n===============')
    return 'success'

def predict_gender(name): 
    
    #loading data and images
    image_path = source+name
    m = re.search('.*(?=-)', name)
    if m:
        found = m.group(0)
    else:
        found = name
    result = {'male': 0, 'female': 0, 'domain':found}
    
    try:
        rgb_image = load_image(image_path, grayscale=False)
    except:
        print('3. Doesn"t open')
        if(os.path.isfile(image_path)):
            os.remove(image_path)
        to_remove.append(name)
        return result
    gray_image = load_image(image_path, grayscale=True)
    gray_image = np.squeeze(gray_image)
    gray_image = gray_image.astype('uint8')

    #face and gender detection
    faces = detect_faces(face_detection, gray_image)
    if (len(faces) == 0):
        print('no faces')
        to_remove.append(name)
    
    for face_coordinates in faces:
        x1, x2, y1, y2 = apply_offsets(face_coordinates, gender_offsets)
        rgb_face = rgb_image[y1:y2, x1:x2]

        try:
            rgb_face = cv2.resize(rgb_face, (gender_target_size))
        except:
            continue

        rgb_face = preprocess_input(rgb_face, False)
        rgb_face = np.expand_dims(rgb_face, 0)
        gender_prediction = gender_classifier.predict(rgb_face)
        gender_label_arg = np.argmax(gender_prediction)
        gender_text = gender_labels[gender_label_arg]

        if gender_text == gender_labels[0]:
            result['female'] += 1
        else:
            result['male'] += 1
    return result

# Read points from text files in directory
def readPoints(path) :
    # Create an array of array of points.
    pointsArray = [];
    #List all files in the directory and read points from text files one by one
    for filePath in sorted(os.listdir(path)):        
        if filePath.endswith(".txt"):            
            #Create an array of points.
            points = [];                        
            # Read points from filePath
            with open(os.path.join(path, filePath)) as file :
                for line in file :
                    x, y = line.split()
                    points.append((int(x), int(y)))          
            # Store array of points
            pointsArray.append(points)            
    return pointsArray[:150];

# Read all jpg images in folder.
def readImages(path) :    
    #Create array of array of images.
    imagesArray = [];   
    #List all files in the directory and read points from text files one by one
    for filePath in sorted(os.listdir(path)):
        if filePath.endswith(".jpg"):
            # Read image found.
            img = cv2.imread(os.path.join(path,filePath));
            # Convert to floating point
            img = np.float32(img)/255.0;
            # Add to array of images
            imagesArray.append(img);            
    return imagesArray[:150];
                
# Compute similarity transform given two sets of two points.
def similarityTransform(inPoints, outPoints) :
    s60 = math.sin(60*math.pi/180);
    c60 = math.cos(60*math.pi/180);  
 
    inPts = np.copy(inPoints).tolist();
    outPts = np.copy(outPoints).tolist();
    
    xin = c60*(inPts[0][0] - inPts[1][0]) - s60*(inPts[0][1] - inPts[1][1]) + inPts[1][0];
    yin = s60*(inPts[0][0] - inPts[1][0]) + c60*(inPts[0][1] - inPts[1][1]) + inPts[1][1];    
    inPts.append([np.int(xin), np.int(yin)]);    
    xout = c60*(outPts[0][0] - outPts[1][0]) - s60*(outPts[0][1] - outPts[1][1]) + outPts[1][0];
    yout = s60*(outPts[0][0] - outPts[1][0]) + c60*(outPts[0][1] - outPts[1][1]) + outPts[1][1];
    
    outPts.append([np.int(xout), np.int(yout)]);    
    tform = cv2.estimateRigidTransform(np.array([inPts]), np.array([outPts]), False);    
    return tform;

# Check if a point is inside a rectangle
def rectContains(rect, point) :
    if point[0] < rect[0] :
        return False
    elif point[1] < rect[1] :
        return False
    elif point[0] > rect[2] :
        return False
    elif point[1] > rect[3] :
        return False
    return True

# Calculate delanauy triangle
def calculateDelaunayTriangles(rect, points):
    # Create subdiv
    subdiv = cv2.Subdiv2D(rect);  
    # Insert points into subdiv
    for p in points:
        subdiv.insert((p[0], p[1]));   
    # List of triangles. Each triangle is a list of 3 points ( 6 numbers )
    triangleList = subdiv.getTriangleList();
    # Find the indices of triangles in the points array
    delaunayTri = []    
    for t in triangleList:
        pt = []
        pt.append((t[0], t[1]))
        pt.append((t[2], t[3]))
        pt.append((t[4], t[5]))
        
        pt1 = (t[0], t[1])
        pt2 = (t[2], t[3])
        pt3 = (t[4], t[5])        
        
        if rectContains(rect, pt1) and rectContains(rect, pt2) and rectContains(rect, pt3):
            ind = []
            for j in range(0, 3):
                for k in range(0, len(points)):                    
                    if(abs(pt[j][0] - points[k][0]) < 1.0 and abs(pt[j][1] - points[k][1]) < 1.0):
                        ind.append(k)                            
            if len(ind) == 3:                                                
                delaunayTri.append((ind[0], ind[1], ind[2]))   
    return delaunayTri


def constrainPoint(p, w, h) :
    p =  ( min( max( p[0], 0 ) , w - 1 ) , min( max( p[1], 0 ) , h - 1 ) )
    return p;

# output an image of size.
def applyAffineTransform(src, srcTri, dstTri, size) :   
    # Given a pair of triangles, find the affine transform.
    warpMat = cv2.getAffineTransform( np.float32(srcTri), np.float32(dstTri) )   
    dst = cv2.warpAffine( src, warpMat, (size[0], size[1]), None, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101 )
    return dst

# Warps and alpha blends triangular regions from img1 and img2 to img
def warpTriangle(img1, img2, t1, t2) :
    # Find bounding rectangle for each triangle
    r1 = cv2.boundingRect(np.float32([t1]))
    r2 = cv2.boundingRect(np.float32([t2]))
    # Offset points by left top corner of the respective rectangles
    t1Rect = [] 
    t2Rect = []
    t2RectInt = []
    for i in range(0, 3):
        t1Rect.append(((t1[i][0] - r1[0]),(t1[i][1] - r1[1])))
        t2Rect.append(((t2[i][0] - r2[0]),(t2[i][1] - r2[1])))
        t2RectInt.append(((t2[i][0] - r2[0]),(t2[i][1] - r2[1])))
    # Get mask by filling triangle
    mask = np.zeros((r2[3], r2[2], 3), dtype = np.float32)
    cv2.fillConvexPoly(mask, np.int32(t2RectInt), (1.0, 1.0, 1.0), 16, 0);
    # Apply warpImage to small rectangular patches
    img1Rect = img1[r1[1]:r1[1] + r1[3], r1[0]:r1[0] + r1[2]]    
    size = (r2[2], r2[3])
    img2Rect = applyAffineTransform(img1Rect, t1Rect, t2Rect, size)   
    img2Rect = img2Rect * mask
    # Copy triangular region of the rectangular patch to the output image
    img2[r2[1]:r2[1]+r2[3], r2[0]:r2[0]+r2[2]] = img2[r2[1]:r2[1]+r2[3], r2[0]:r2[0]+r2[2]] * ( (1.0, 1.0, 1.0) - mask )    
    img2[r2[1]:r2[1]+r2[3], r2[0]:r2[0]+r2[2]] = img2[r2[1]:r2[1]+r2[3], r2[0]:r2[0]+r2[2]] + img2Rect

def calc_average():    
    my_path = '/home/gc1569/Image_collector/img/'+ id 
    path = my_path +'/processed/'    
    # Dimensions of output image
    w = 600;
    h = 600;
    # Read points for all images
    allPoints = readPoints(path);    
    images = readImages(path);
    if (len(images) < 2):
        return
    # Eye corners
    eyecornerDst = [ (np.int(0.3 * w ), np.int(h / 3)), (np.int(0.7 * w ), np.int(h / 3)) ];    
    imagesNorm = [];
    pointsNorm = [];
    
    # Add boundary points for delaunay triangulation
    boundaryPts = np.array([(0,0), (w/2,0), (w-1,0), (w-1,h/2), ( w-1, h-1 ), ( w/2, h-1 ), (0, h-1), (0,h/2) ]);    
    # Initialize location of average points to 0s
    pointsAvg = np.array([(0,0)]* ( len(allPoints[0]) + len(boundaryPts) ), np.float32());
    
    n = len(allPoints[0]);
    numImages = len(images)
    
    # Warp images and trasnform landmarks to output coordinate system,and find average of transformed landmarks.    
    for i in range(0, numImages):
        points1 = allPoints[i];
        # Corners of the eye in input image
        eyecornerSrc  = [ allPoints[i][36], allPoints[i][45] ]       
        # Compute similarity transform
        tform = similarityTransform(eyecornerSrc, eyecornerDst);       
        # Apply similarity transformation
        img = cv2.warpAffine(images[i], tform, (w,h))
        # Apply similarity transform on points
        points2 = np.reshape(np.array(points1), (68,1,2));                
        points = cv2.transform(points2, tform);        
        points = np.float32(np.reshape(points, (68, 2)));       
        # Append boundary points. Will be used in Delaunay Triangulation
        points = np.append(points, boundaryPts, axis=0)       
        # Calculate location of average landmark points.
        pointsAvg = pointsAvg + points / numImages;        
        pointsNorm.append(points);
        imagesNorm.append(img);
    
    # Delaunay triangulation
    rect = (0, 0, w, h);
    dt = calculateDelaunayTriangles(rect, np.array(pointsAvg));

    # Output image
    output = np.zeros((h,w,3), np.float32());

    # Warp input images to average image landmarks
    for i in range(0, len(imagesNorm)) :
        img = np.zeros((h,w,3), np.float32());
        # Transform triangles one by one
        for j in range(0, len(dt)) :
            tin = []; 
            tout = [];            
            for k in range(0, 3) :                
                pIn = pointsNorm[i][dt[j][k]];
                pIn = constrainPoint(pIn, w, h);
                
                pOut = pointsAvg[dt[j][k]];
                pOut = constrainPoint(pOut, w, h);
                
                tin.append(pIn);
                tout.append(pOut);            
            warpTriangle(imagesNorm[i], img, tin, tout);
        # Add image intensities for averaging
        output = output + img;
    # Divide by numImages to get average
    output = output / numImages;

    # save image
    plt.imsave('/home/gc1569/Image_collector/public/img/' + id + "-average.jpg", cv2.cvtColor(output, cv2.COLOR_BGR2RGB))
    
def calc_tile():
    my_path = '/home/gc1569/Image_collector/img/'+id
    files = [ join(my_path+'/processed', f) for f in listdir(my_path+'/processed') if isfile(join(my_path+'/processed', f)) and not f.endswith('.txt')]
    
    random.shuffle(files)
    new_im = Image.new('RGB', (2000,2000))
    index = 0
    for i in range(0,2000,200):
        for j in range(0,2000,200):
            try:
                image = Image.open(files[index])
            except:
                break
            width  = image.size[0]
            height = image.size[1]

            aspect = width / float(height)

            ideal_width = 200
            ideal_height = 200

            ideal_aspect = ideal_width / float(ideal_height)

            if aspect > ideal_aspect:
                # Then crop the left and right edges:
                new_width = int(ideal_aspect * height)
                offset = (width - new_width) / 2
                resize = (offset, 0, width - offset, height)
            else:
                # ... crop the top and bottom:
                new_height = int(width / ideal_aspect)
                offset = (height - new_height) / 2
                resize = (0, offset, width, height - offset)

            thumb = image.crop(resize).resize((ideal_width, ideal_height), Image.ANTIALIAS)
            new_im.paste(thumb, (i,j))
            index += 1
    new_im.save('/home/gc1569/Image_collector/public/img/' + id + "-tile.jpg")


#Read data from stdin
def read_in():
    lines = sys.stdin.readlines()
    return json.loads(lines[0])

def combine_json(data):
    my_dict = {}
    for b in data:
        if (b['domain'] in my_dict):
            my_dict[b['domain']]['male'] += b['male']
            my_dict[b['domain']]['female'] += b['female']
        else:
            my_dict[b['domain']] = {}
            my_dict[b['domain']]['male'] = b['male']
            my_dict[b['domain']]['female'] = b['female']
    return [{'domain': key, 'female': value['female'], 'male': value['male']} for key, value in my_dict.items()]


#start process
if __name__ == '__main__':
    print('preprocessing')
    no_removes = 0
    #get our data as an array from read_in()
    id = sys.argv[1]
    data = read_in()
    print('Original data length: ', len(data))
    source = '/home/gc1569/Image_collector/img/'+id+'/raw/'
    destination = '/home/gc1569/Image_collector/img/'+id+'/processed/'
    for f in data:
        if(not os.path.isfile(source+f)):
            print('1. not file')
            no_removes += 1
            data.remove(f)
        elif (imghdr.what(source+f) is None or os.stat(source+f).st_size < 3000):
            print('2. Small or not image')
            no_removes += 1
            os.remove(source+f)
            data.remove(f)


    to_remove = []
    output = map(predict_gender, data)
    for i in to_remove:
        no_removes += 1
        data.remove(i)
    genders = [i for i in list(output) if i['male']+i['female'] > 0]
    
    summary = genders
    try:
        download1 = json.load(open('/home/gc1569/Image_collector/public/img/' + id + "-stats.json", 'r'))
        summary = combine_json(summary + download1)
    except Exception as e: 
        print(e)    
    with open('./public/img/'+id+'-stats.json', 'w') as outfile:
        json.dump(summary, outfile)
    
    global_sum = genders
    try:
        download2 = json.load(open('/home/gc1569/Image_collector/public/img/global-sum.json', 'r'))
        global_sum = combine_json(global_sum + download2)
    except Exception as e: 
        print(e)
    with open('/home/gc1569/Image_collector/public/img/global-sum.json', 'w') as outfile:
        json.dump(global_sum, outfile)
    
    
    print('N.o. removes: ', no_removes, ' | N.o. Results: ', len(genders))
    output = map(align_face, list(data))
    print('Alignment done:', list(output))
    
    calc_tile()
    calc_average()
    print('Images created')
