const WIDTH = 500;

PIXI.utils.skipHello();
PIXI.live2d.config.logLevel = PIXI.live2d.config.LOG_LEVEL_NONE;

function getModelHeadBounds(model) {
    const areas = model.internalModel.hitAreas;

    // check if head or Head exists
    head = areas["head"] ?? areas["Head"];
    if (head == undefined) {
        console.log("no head found");
        return;
    }

    // https://github.com/guansss/pixi-live2d-display/blob/7d20ff713c28e3e8f263196b33ccc8f7cf3ad1a0/src/cubism-common/InternalModel.ts#L212
    const bounds = model.internalModel.getDrawableBounds(head.index);

    return bounds;
}

function transformBounds(bounds, model) {
    const transform = model.localTransform;
    bounds.x = bounds.x * transform.a + transform.tx;
    bounds.y = bounds.y * transform.d + transform.ty;
    bounds.width = bounds.width * transform.a;
    bounds.height = bounds.height * transform.d;

    return bounds;
}

// on load
window.onload = function () {
    const app = new PIXI.Application({
        view: document.getElementById("canvas"),
        autoStart: true,
        width: WIDTH,
        height: window.innerHeight,
    });

    $(window).resize(function () {
        app.renderer.resize(WIDTH, window.innerHeight);
    });

    // mild face following
    window.face_coordinates = () => {
        let bounds = getModelHeadBounds(model);

        if (bounds == undefined) {
            return;
        }

        bounds = transformBounds(bounds, model);

        let headcenter = new PIXI.Point(
            bounds.x + bounds.width / 2,
            bounds.y + bounds.height / 2
        );

        let movement = new PIXI.Point(
            window.face_coordinates.x * bounds.width - bounds.width / 2,
            window.face_coordinates.y * bounds.height - bounds.height / 2
        );

        let canvaspos = new PIXI.Point(
            headcenter.x + movement.x,
            headcenter.y + movement.y
        );

        model.focus(canvaspos.x, canvaspos.y);
    };

    var model;

    var mutex = false;
    var last = null;

    $("#waifu-selector").change(async function () {
        var selected = $(this).children("option:selected").val();

        last = selected;
        setTimeout(async function () {
            if (mutex || last != selected) {
                return;
            }

            mutex = true;

            app.stage.removeChildren();
            model = await PIXI.live2d.Live2DModel.from(selected, {
                autoInteract: false,
            });

            var model_width = model.width;
            model.scale.set(WIDTH / model_width);
            app.stage.addChild(model);

            mutex = false;

            if (last != selected) {
                $("#waifu-selector").change();
            }

            if (getModelHeadBounds(model) == undefined) {
                $("#face-following").prop("disabled", true);
                $("#face-following").prop("checked", false);
            } else {
                $("#face-following").prop("disabled", false);
            }
        }, 750);
    });
    $("#face-following").change(function () {
        if ($(this).is(":checked")) {
            window.face_callback();
            model.on("update", window.face_callback);
        } else {
            model.off("update", window.face_callback);
        }

    $("#waifu-selector").change();
};
