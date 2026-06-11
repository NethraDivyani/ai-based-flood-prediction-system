document.addEventListener("DOMContentLoaded", function () {
    const langSwitch = document.getElementById("langSwitch");
    if (langSwitch) {
        const savedLang = localStorage.getItem("site_lang");
        if (savedLang) {
            langSwitch.value = savedLang;
        }

        langSwitch.addEventListener("change", function () {
            localStorage.setItem("site_lang", this.value);
        });
    }

    const progressBars = document.querySelectorAll(".progress-bar[data-width]");
    progressBars.forEach(function (bar) {
        const width = bar.getAttribute("data-width");
        bar.style.width = width + "%";
    });
});