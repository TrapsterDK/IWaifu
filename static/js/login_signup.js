function login_signup_form_handler(form, url) {
    $("#error").hide();

    $.ajax({
        type: "POST",
        url: url,
        data: $(form).serialize(),
        success: function (data) {
            if (data === "success") {
                $(location).prop("href", "/");
            } else {
                console.log(data);
                $("#server-error").html(data);
                $("#server-error").show();
            }
        },
    });
}
