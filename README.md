# Visual Gender Bias Detector

I hypothesised that websites would be biased towards a single gender based on the target groups and content of the website. To measure the differences, I designed a multi layered system based on a chrome extension collecting images, a node server, calling python scripts processing images, and a D3 JS front-end to visualize the results. As an introduction I will walk through each component and what it does.
## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Node.JS.

- OpenCV, Anaconda, Keras, DLIB for python 3 

### Installing

After cloning it and installing prerequisites, run

```
npm install
```
to install node modules. After that just type 

```
node server.js
```
and the server should be up and running on localhost:8002.

You also need the chrome extension running in Google Chrome to collect images, which you load on the extensions page of Chrome.

## Components 
### Chrome extension
Through the Webrequest Chrome API, any chrome extension can get permission to see and collect web request made to servers. My extension is listening for these requests made, and saves the ones that have an image data type. Once we have 150 urls or the user presses the “send” button on the popup, the list of urls is sent to the server to be evaluated. In the popup, you can also start/stop recording, request the results of your data collection, and empty the storage.

### Server
The heart of the application is a node server, that listens for incoming urls. If received, it will download every image that is above 5kB (smaller than that is too small to find faces), and call a python script to evaluate whether the images contain faces and what their genders are. I don’t filter out duplicates, because even if a user opens BBC 5 times a day and sees the same male face, that face is still viewed five times. If a visualization is requested from the server, it calls another python process, to create the information visualization for the front-end component of the project. Then it sends an html as response.

### Python scripts
Using a pre trained CNN by the B-IT-BOTS robotics team 6, the script first counts the number of male and female faces presented in each image. The robotics team reports accuracies of 96% in the IMDB gender dataset and their model has been used in thousands of projects. Understandably, most pictures don’t contain faces, therefore they are deleted. The second function of this script is to prepare the visualizations created from these images. Using DLIB and OPENCV, the script crops each image to the face, detects landmark points on the images and creates a distortion that corresponds to the average of these faces 7. It also creates a tile of 100 images to see specific faces.

## Contributing

Please feel free to reach out to me, if you would like to contribute by improving the gender . It is a great service to our school.


## Authors

* **Gabor Csapo** - gabor.csapo@nyu.edu
