function getBubbleTemplate(message, timestamp, type) {
    return `
        <div class="bubblewrap">
            <div class="bubble bubble-${type}">
                <div class="bubble-content">
                    <p>${message}</p>
                </div>
                <div class="chat-timestamp ${type}">${timestamp}</div>
            </div>
        </div>
    `;
}

function refresh_chat() {
    $.ajax({
        url: "/chat",
        type: "POST",
        data: {
            waifu: $("#waifu-selector option:selected").text(),
        },
        success: function (json) {
            let chat = $("#chat");
            chat.empty();

            for (let i = 0; i < json.length; i++) {
                chat.append(
                    getBubbleTemplate(
                        json[i].message,
                        json[i].time,
                        json[i].from_user ? "send" : "recieve"
                    )
                );
            }

            chat.scrollTop(chat.prop("scrollHeight"));
        },
    });
}

$(document).ready(function () {
    refresh_chat();

    $("#chat-form").on("submit", function (event) {
        let chat_input = $("#chat-input");

        if (!chat_input.val().trim()) {
            return false;
        }

        let chat = $("#chat");
        let time = new Date().toLocaleTimeString(
            {},
            { hour: "2-digit", minute: "2-digit" }
        );

        chat.append(getBubbleTemplate(chat_input.val(), time, "send"));
        chat.scrollTop(chat.prop("scrollHeight"));

        let speech = $("#speech").prop("checked");

        $.ajax({
            url: "/chat",
            type: "POST",
            data: {
                message: chat_input.val(),
                waifu: $("#waifu-selector option:selected").text(),
                speech: speech,
            },
            success: function (json) {
                chat.append(
                    getBubbleTemplate(json.message, json.time, "recieve")
                );
                chat.scrollTop(chat.prop("scrollHeight"));

                if (speech) {
                    var audio = new Audio("/animevoiceresponce");
                    audio.play();
                }
            },
        });

        chat_input.val("");
    });
});
