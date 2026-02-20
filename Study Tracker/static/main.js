/* =================================================
   GLOBAL SAFE INIT
================================================= */

document.addEventListener("DOMContentLoaded", () => {

    initTheme();
    initDropdown();
    initSearchFilter();
    initGoalTracker();

});


/* =================================================
   DARK MODE
================================================= */

function initTheme() {

    const toggleBtn = document.getElementById("themeToggle");
    const root = document.documentElement;

    if (!toggleBtn) return;

    const savedTheme = localStorage.getItem("theme");

    if (savedTheme === "dark") {
        root.setAttribute("data-theme", "dark");
        toggleBtn.textContent = "☀️ Light Mode";
    }

    toggleBtn.addEventListener("click", () => {

        const isDark = root.getAttribute("data-theme") === "dark";

        if (isDark) {
            root.removeAttribute("data-theme");
            localStorage.setItem("theme", "light");
            toggleBtn.textContent = "🌙 Dark Mode";
        } else {
            root.setAttribute("data-theme", "dark");
            localStorage.setItem("theme", "dark");
            toggleBtn.textContent = "☀️ Light Mode";
        }

    });

}


/* =================================================
   DROPDOWN MENU
================================================= */

function initDropdown() {

    const avatarBtn = document.getElementById("avatarBtn");
    const dropdown = document.getElementById("dropdownMenu");

    if (!avatarBtn || !dropdown) return;

    avatarBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("show");
    });

    document.addEventListener("click", () => {
        dropdown.classList.remove("show");
    });

}


/* =================================================
   SEARCH & FILTER
================================================= */

function initSearchFilter() {

    const searchInput = document.getElementById("searchInput");
    const difficultyFilter = document.getElementById("difficultyFilter");
    const fromDate = document.getElementById("fromDate");
    const toDate = document.getElementById("toDate");
    const clearBtn = document.getElementById("clearFilter");
    const table = document.getElementById("logTable");

    if (!table) return;

    function filterTable() {

        const searchText = searchInput?.value.toLowerCase() || "";
        const diffVal = difficultyFilter?.value || "";
        const from = fromDate?.value || "";
        const to = toDate?.value || "";

        const rows = table.querySelectorAll("tbody tr");

        rows.forEach(row => {

            const date = row.children[0].innerText;
            const subject = row.children[1].innerText.toLowerCase();
            const topic = row.children[2].innerText.toLowerCase();
            const difficulty = row.children[4].innerText;

            let show = true;

            // Text search
            if (searchText &&
                !subject.includes(searchText) &&
                !topic.includes(searchText)) {
                show = false;
            }

            // Difficulty
            if (diffVal && difficulty !== diffVal) {
                show = false;
            }

            // Date range
            if (from && date < from) show = false;
            if (to && date > to) show = false;

            row.style.display = show ? "" : "none";

        });

    }

    searchInput?.addEventListener("input", filterTable);
    difficultyFilter?.addEventListener("change", filterTable);
    fromDate?.addEventListener("change", filterTable);
    toDate?.addEventListener("change", filterTable);

    clearBtn?.addEventListener("click", () => {

        searchInput.value = "";
        difficultyFilter.value = "";
        fromDate.value = "";
        toDate.value = "";

        filterTable();

    });

}


/* =================================================
   WEEKLY GOAL TRACKER (Frontend UI Only)
================================================= */

function initGoalTracker() {
    const resetBtn = document.getElementById("resetGoalBtn");

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            localStorage.removeItem("weeklyGoal");
        });
    }

    const goalText = document.getElementById("goalText");
    const progressFill = document.getElementById("progressFill");
    const table = document.getElementById("logTable");

    if (!goalText || !progressFill || !table) return;

    const weeklyGoal = parseFloat(localStorage.getItem("weeklyGoal"));

    if (!weeklyGoal || weeklyGoal <= 0) {
        goalText.innerHTML = "Weekly goal not set";
        progressFill.style.width = "0%";
        return;
    }


    function getCurrentWeekHours() {

        let total = 0;

        const rows = table.querySelectorAll("tbody tr");

        rows.forEach(row => {

            const dateText = row.children[0].innerText;
            const hours = parseFloat(row.children[3].innerText);

            const logDate = new Date(dateText);
            const now = new Date();

            const diff = (now - logDate) / (1000 * 60 * 60 * 24);

            if (diff <= 7) {
                total += hours;
            }

        });

        return total;
    }

    const studied = getCurrentWeekHours();
    const percent = Math.min((studied / weeklyGoal) * 100, 100);

    progressFill.style.width = percent + "%";

    let status = "ON TRACK 🚀";

    if (percent < 50) status = "BEHIND ⚠️";
    if (percent < 25) status = "DANGER 🔴";

    goalText.innerHTML =
        `Studied: <b>${studied.toFixed(1)}</b> / ${weeklyGoal} hrs | ${status}`;

}
