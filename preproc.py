import sys, os
sys.path.append(os.path.abspath("/home/gc1569/Capstone/Landmark_Detection/dlib/python_examples"))
sys.path.append(os.path.abspath("/home/gc1569/Image_collector/face_classification/src/utils"))
sys.path.append(os.path.abspath("/home/gc1569/Image_collector/face_classification/src"))

import numpy as np
from skimage import io
from inference import draw_text
from datasets import get_labels
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


#Read data from stdin
def read_in():
    lines = sys.stdin.readlines()
    return json.loads(lines[0])


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
    #{a['name']:{'male': a['male'], 'female': a['female']} for a in list(output) if a['male']+a['female'] > 0}

    if (os.path.isfile('./public/img/'+id+'-stats.json')):
        if (os.stat('./public/img/'+id+'-stats.json').st_size != 0):
            json_data = json.load(open('./public/img/'+id+'-stats.json', 'r'))
            json_data = genders + json_data
            with open('./public/img/'+id+'-stats.json', 'w') as outfile:
                json.dump(json_data, outfile)
        else:
            with open('./public/img/'+id+'-stats.json', 'w') as outfile:
                json.dump(genders, outfile)
    else:
        with open('./public/img/'+id+'-stats.json', 'w') as outfile:
            json.dump(genders, outfile)
    print('N.o. removes: ', no_removes, ' | N.o. Results: ', len(genders))
    output = map(align_face, list(data))
    print('Alignment done:', list(output))

