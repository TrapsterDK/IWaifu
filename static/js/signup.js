$.validator.addMethod("lowercase", function (value) {
    return /[a-z]/.test(value);
});

$.validator.addMethod("uppercase", function (value) {
    return /[A-Z]/.test(value);
});

$.validator.addMethod("number", function (value) {
    return /[0-9]/.test(value);
});

$(document).ready(function () {
    $("#signup-form").validate({
        rules: {
            username: {
                required: true,
                minlength: 4,
                maxlength: 20,
            },
            password: {
                required: true,
                minlength: 6,
                maxlength: 32,
                lowercase: true,
                uppercase: true,
                number: true,
            },
            verify: {
                required: true,
                minlength: 6,
                maxlength: 32,
                equalTo: "#password",
            },
            email: {
                required: true,
                email: true,
            },
        },
        messages: {
            username: {
                required: "Please enter a username",
                minlength:
                    "Your username must consist of at least 4 characters",
                maxlength: "Your username must be less than 20 characters",
            },
            password: {
                required: "Please provide a password",
                minlength: "Your password must be at least 6 characters long",
                maxlength: "Your password must be less than 20 characters",
                lowercase:
                    "Your password must contain at least one lowercase letter",
                uppercase:
                    "Your password must contain at least one uppercase letter",
                number: "Your password must contain at least one number",
            },
            verify: {
                required: "Please provide a password",
                minlength: "Your password must be at least 6 characters long",
                maxlength: "Your password must be less than 20 characters",
                equalTo: "Please enter the same password as above",
            },
            email: "Please enter a valid email address",
        },
        submitHandler: function (form) {
            $.ajax({
                type: "POST",
                url: "/signup",
                data: $(form).serialize(),
                success: function (data) {
                    if (data === 1) {
                        window.location.href = "/";
                    } else {
                        $("#error").html(data);
                        $("#error").show();
                    }
                },
            });
        },
    });
});