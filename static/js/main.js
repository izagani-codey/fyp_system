// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            if (alert && alert.parentElement) {
                alert.style.transition = 'opacity 0.4s';
                alert.style.opacity = '0';
                setTimeout(function () { alert.remove(); }, 400);
            }
        }, 5000);
    });
});
