/*
// expression estimate, 0 = not present, 1 = present
window.expression = {
    angry: 0,
    disgusted: 0,
    fearful: 0,
    happy: 0,
    neutral: 0,
    sad: 0,
    surprised: 0,
};

// start age estimate at 20
window.age = 20;

// gender estimate, 0 = male, 1 = female
window.gender = 0.5;
*/

// estimated position of the face, 0 to 1s
window.face_coordinates = {
    x: 0.5,
    y: 0.5,
};

// load the models
Promise.all([
    faceapi.nets.tinyFaceDetector.loadFromUri(
        "https://cdn.jsdelivr.net/gh/cgarciagl/face-api.js@0.22.2/weights"
    ),
    /*
    faceapi.nets.faceLandmark68Net.loadFromUri(
        "https://cdn.jsdelivr.net/gh/cgarciagl/face-api.js@0.22.2/weights"
    ),
    faceapi.nets.faceExpressionNet.loadFromUri(
        "https://cdn.jsdelivr.net/gh/cgarciagl/face-api.js@0.22.2/weights"
    ),
    faceapi.nets.ageGenderNet.loadFromUri(
        "https://cdn.jsdelivr.net/gh/cgarciagl/face-api.js@0.22.2/weights"
    ),
    */
]);

// start the video
function startVideo() {
    if (
        !"mediaDevices" in navigator ||
        !"getUserMedia" in navigator.mediaDevices
    ) {
        console.log("Camera is not supported by your browser");
        return;
    }

    navigator.mediaDevices
        .getUserMedia({
            video: {
                width: { ideal: 320 },
                height: { ideal: 240 },
            },
        })
        .then((stream) => {
            video.srcObject = stream;
            video.play();
        })
        .catch((err) => {
            console.log("video not started");
            console.log(err);
        });
}

function StopVideo() {
    video.pause();
    video.srcObject = null;
}

$(document).ready(function () {
    // https://github.com/justadudewhohacks/face-api.js/
    const video = $("#video").get(0);
    let facedetector = new faceapi.TinyFaceDetectorOptions();

    // when the video metadata is loaded, start the detection
    video.addEventListener("loadedmetadata", async () => {
        console.log("video started");
        // update the values every 10ms
        setInterval(async () => {
            // detect the face
            const singleFace = await faceapi.detectSingleFace(
                video,
                facedetector
            );
            /*
                .withFaceLandmarks()
                .withFaceExpressions()
                .withAgeAndGender();
                */

            // if no face is detected, return
            if (singleFace === undefined) return;

            // calculate the expression estimate by averaging the current estimate with the new estimate
            /*
            window.expression = {
                angry:
                    singleFace.expressions.angry * 0.05 +
                    window.expression.angry * 0.95,
                disgusted:
                    singleFace.expressions.disgusted * 0.05 +
                    window.expression.disgusted * 0.95,
                fearful:
                    singleFace.expressions.fearful * 0.05 +
                    window.expression.fearful * 0.95,
                happy:
                    singleFace.expressions.happy * 0.05 +
                    window.expression.happy * 0.95,
                neutral:
                    singleFace.expressions.neutral * 0.05 +
                    window.expression.neutral * 0.95,
                sad: singleFace.expressions.sad * 0.05 + expression.sad * 0.95,
                surprised:
                    singleFace.expressions.surprised * 0.05 +
                    window.expression.surprised * 0.95,
            };

            // gender exists of probabilty and gender
            let genderEstimate =
                singleFace.gender == "male"
                    ? singleFace.genderProbability
                    : 1 - singleFace.genderProbability;
            window.gender = genderEstimate * 0.05 + window.gender * 0.95;

            // calculate the age estimate by averaging the current estimate with the new estimate
            window.age = singleFace.age * 0.05 + window.age * 0.95;
            */

            // detection point is the center of the box of the face
            window.face_coordinates = {
                x:
                    (1 -
                        (singleFace.box.x + singleFace.box.width / 2) /
                            video.videoWidth) *
                        singleFace.score +
                    window.face_coordinates.x * (1 - singleFace.score),
                y:
                    (1 -
                        (singleFace.box.y + singleFace.box.height / 2) /
                            video.videoHeight) *
                        singleFace.score +
                    window.face_coordinates.y * (1 - singleFace.score),
            };
        }, 1000);
    });

    // start the video
    startVideo();
});
