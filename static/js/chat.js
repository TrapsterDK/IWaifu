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

$(document).ready(function () {
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

        $.ajax({
            url: "/chat",
            type: "POST",
            data: {
                message: chat_input.val(),
                waifu: $("#waifu-selector option:selected").text(),
            },
            success: function (json) {
                chat.append(
                    getBubbleTemplate(json.message, json.time, "recieve")
                );
                chat.scrollTop(chat.prop("scrollHeight"));

                var audio = new Audio(json.audio);
                audio.play();
            },
        });

        chat_input.val("");
    });
});
