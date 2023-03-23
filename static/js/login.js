$(document).ready(function () {
    $("#login-signup-form").validate({
        rules: {
            username: {
                required: true,
            },
            password: {
                required: true,
            },
        },
        messages: {
            username: {
                required: "Please enter a username",
            },
            password: {
                required: "Please provide a password",
            },
        },
        submitHandler: function (form) {
            login_signup_form_handler(form, "/login");
        },
    });
});
