function login_signup_form_handler(form, url) {
    $("#error").hide();

    $.ajax({
        type: "POST",
        url: url,
        data: $(form).serialize(),
        success: function (data) {
            console.log(data);
            if (data === 1) {
                window.location.href = "/";
            } else {
                $("#error").html(data);
                $("#error").show();
            }
        },
    });
}
