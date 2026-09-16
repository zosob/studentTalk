// facultyDigest.js
// Powers the "Weekly digest" and "Register an assignment deadline" sections
// added to faculty.html. Talks to the /faculty_digest and /deadlines
// endpoints added in main.py.

async function loadDigest() {
    const statsEl = document.getElementById("digestStats");
    const bodyEl = document.getElementById("digestBody");
    const statusEl = document.getElementById("digestStatus");

    statusEl.textContent = "Loading...";
    bodyEl.innerHTML = "";
    statsEl.innerHTML = "";

    try {
        const res = await fetch("/faculty_digest");
        const data = await res.json();

        statsEl.innerHTML = `
            <div class="stat"><b>${data.active_students}</b>Active students</div>
            <div class="stat"><b>${data.total_messages}</b>Messages this week</div>
            <div class="stat"><b>${data.total_flags}</b>Wellbeing flags</div>
        `;

        const students = Object.entries(data.student_summary);
        if (students.length === 0) {
            bodyEl.innerHTML = `<tr><td colspan="4">No activity in the last 7 days.</td></tr>`;
        } else {
            for (const [studentId, summary] of students) {
                const row = document.createElement("tr");
                if (data.at_risk_students.includes(studentId)) {
                    row.className = "flagged-row";
                }
                row.innerHTML = `
                    <td>${studentId}</td>
                    <td>${summary.message_count}</td>
                    <td>${summary.avg_wellbeing_score ?? "—"}</td>
                    <td>${summary.flag_count}</td>
                `;
                bodyEl.appendChild(row);
            }
        }

        statusEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (err) {
        statusEl.textContent = "Failed to load digest: " + err.message;
    }
}

async function addDeadline() {
    const statusEl = document.getElementById("deadlineStatus");
    const assignment_id = document.getElementById("deadlineId").value.trim();
    const course = document.getElementById("deadlineCourse").value.trim();
    const title = document.getElementById("deadlineTitle").value.trim();
    const due = document.getElementById("deadlineDue").value;

    if (!assignment_id || !course || !title || !due) {
        statusEl.textContent = "Fill in all fields first.";
        return;
    }

    try {
        const res = await fetch("/deadlines", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ assignment_id, course, title, due }),
        });
        const data = await res.json();
        statusEl.textContent = data.message || data.error;
        loadDeadlines();
    } catch (err) {
        statusEl.textContent = "Failed to add deadline: " + err.message;
    }
}

async function loadDeadlines() {
    const bodyEl = document.getElementById("deadlineBody");
    try {
        const res = await fetch("/deadlines");
        const data = await res.json();
        const entries = Object.entries(data);

        bodyEl.innerHTML = entries.length === 0
            ? `<tr><td colspan="3">No deadlines registered yet.</td></tr>`
            : "";

        for (const [assignmentId, info] of entries) {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${assignmentId} — ${info.title}</td>
                <td>${info.course}</td>
                <td>${new Date(info.due).toLocaleString()}</td>
            `;
            bodyEl.appendChild(row);
        }
    } catch (err) {
        console.error("Failed to load deadlines:", err);
    }
}

// Load both on page open
window.addEventListener("DOMContentLoaded", () => {
    loadDigest();
    loadDeadlines();
});